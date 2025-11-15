"""Media source implementation for the Noise Generator integration."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, unquote

from homeassistant.components.media_source import (
    MediaSource,
    MediaSourceError,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.components.media_source import const as media_source_const
from homeassistant.core import HomeAssistant

try:  # pragma: no cover - compatibility shim
    from homeassistant.components.media_source import BrowseMedia
except ImportError:  # pragma: no cover - HA 2024.10+
    BrowseMedia = None  # type: ignore[assignment]
    from homeassistant.components.media_source import BrowseMediaSource
    from homeassistant.components.media_player.const import MediaClass, MediaType

from .const import DOMAIN, MEDIA_MIME_TYPE
from .stream import NoiseStreamManager, NoiseStreamProfile


async def async_get_media_source(hass: HomeAssistant) -> "NoiseGeneratorMediaSource":
    """Return the singleton media source for the domain."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    source: NoiseGeneratorMediaSource | None = domain_data.get("media_source")
    if source is None:
        source = NoiseGeneratorMediaSource(hass)
        domain_data["media_source"] = source
    return source


class NoiseGeneratorMediaSource(MediaSource):
    """Expose configured noise profiles as a Home Assistant media source."""

    name = "Noise Generator"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    def _single_entry(self) -> tuple[str, NoiseStreamManager] | None:
        domain = self.hass.data.get(DOMAIN, {})
        entries = domain.get("entries", {})
        for stored in entries.values():
            manager: NoiseStreamManager | None = stored.get("manager")
            if manager is None:
                continue
            title = stored.get("title") or self.name
            return title, manager
        return None

    async def async_browse_media(self, item: MediaSourceItem) -> Any:
        """Return the tree for the requested identifier."""

        slug = (item.identifier or "").strip("/")
        if not slug or slug == self.domain:
            return self._build_root_listing()

        entry = self._single_entry()
        if entry is None:
            raise Unresolvable("Noise Generator is not configured")

        entry_title, manager = entry
        profile = manager.get_profile(self._parse_slug(slug))
        if profile is None:
            raise Unresolvable("Profile not found")

        return self._build_profile_node(entry_title, profile)

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Return a playable media payload for the requested profile."""

        slug = self._parse_slug(item.identifier or "")
        entry = self._single_entry()
        if entry is None:
            raise MediaSourceError("Noise Generator is not configured")

        _, manager = entry
        profile = manager.get_profile(slug)
        if profile is None:
            raise MediaSourceError("Unknown profile")

        stream_url = await manager.async_build_stream_url(profile.slug)
        return PlayMedia(stream_url, MEDIA_MIME_TYPE)

    def _parse_slug(self, identifier: str) -> str:
        identifier = identifier.strip("/")
        domain_prefix = f"{self.domain}/"
        if identifier.startswith(domain_prefix):
            identifier = identifier[len(domain_prefix) :]
        if not identifier:
            raise MediaSourceError("Profile identifier missing")
        return unquote(identifier)

    def _build_identifier(self, slug: str) -> str:
        return quote(slug)

    def _format_content_id(self, identifier: str | None) -> str:
        base = f"{media_source_const.URI_SCHEME}{self.domain}"
        if not identifier:
            return base
        return f"{base}/{identifier}"

    def _build_root_listing(self):
        entry = self._single_entry()
        if entry is None:
            raise Unresolvable("Noise Generator is not configured")

        entry_title, manager = entry
        children = [
            self._build_profile_node(entry_title, profile)
            for profile in manager.iter_profiles()
        ]
        thumbnail = self._icon_url()

        if BrowseMedia is not None:
            return BrowseMedia(
                title=self.name,
                media_class=media_source_const.MEDIA_CLASS_DIRECTORY,
                children_media_class=media_source_const.MEDIA_CLASS_MUSIC,
                media_content_id=self._format_content_id(None),
                media_content_type=media_source_const.MEDIA_CLASS_DIRECTORY,
                can_play=False,
                can_expand=True,
                children=children,
                thumbnail=thumbnail,
            )

        return BrowseMediaSource(
            domain=self.domain,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title=self.name,
            can_play=False,
            can_expand=True,
            children=children,
            thumbnail=thumbnail,
        )

    def _build_profile_node(
        self,
        entry_title: str | None,
        profile: NoiseStreamProfile,
    ):
        identifier = self._build_identifier(profile.slug)
        display_name = (
            f"{entry_title} · {profile.name}" if entry_title else profile.name
        )

        if BrowseMedia is not None:
            return BrowseMedia(
                title=display_name,
                media_class=media_source_const.MEDIA_CLASS_MUSIC,
                media_content_id=self._format_content_id(identifier),
                media_content_type=MEDIA_MIME_TYPE,
                can_play=True,
                can_expand=False,
            )

        return BrowseMediaSource(
            domain=self.domain,
            identifier=identifier,
            media_class=MediaClass.MUSIC,
            media_content_type=MEDIA_MIME_TYPE,
            title=display_name,
            can_play=True,
            can_expand=False,
        )

    def _icon_url(self) -> str | None:
        domain = self.hass.data.get(DOMAIN, {})
        return domain.get("icon_url")
