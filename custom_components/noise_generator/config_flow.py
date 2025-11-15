"""Config flow for the Noise Generator integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from .const import (
    ACTION_ADD,
    ACTION_EDIT,
    ACTION_FINISH,
    ACTION_REMOVE,
    CONF_ACTION,
    CONF_CUSTOM_HIGH_CUTOFF,
    CONF_CUSTOM_LOW_CUTOFF,
    CONF_CUSTOM_SLOPE,
    CONF_PROFILE_NAME,
    CONF_PROFILE_PARAMETERS,
    CONF_PROFILE_TYPE,
    CONF_PROFILES,
    CONF_SEED,
    CONF_VOLUME,
    CUSTOM_HIGH_CUTOFF_MAX,
    CUSTOM_LOW_CUTOFF_MIN,
    CUSTOM_SLOPE_MAX,
    CUSTOM_SLOPE_MIN,
    DEFAULT_CUSTOM_HIGH_CUTOFF,
    DEFAULT_CUSTOM_LOW_CUTOFF,
    DEFAULT_CUSTOM_SLOPE,
    DEFAULT_PROFILE_NAME,
    DEFAULT_PROFILE_TYPE,
    DEFAULT_VOLUME,
    DOMAIN,
    PROFILE_TYPES,
)
from .noise import coerce_profile


def _custom_params_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_CUSTOM_SLOPE,
                default=defaults.get(CONF_CUSTOM_SLOPE, DEFAULT_CUSTOM_SLOPE),
            ): vol.All(vol.Coerce(float), vol.Range(min=CUSTOM_SLOPE_MIN, max=CUSTOM_SLOPE_MAX)),
            vol.Required(
                CONF_CUSTOM_LOW_CUTOFF,
                default=defaults.get(CONF_CUSTOM_LOW_CUTOFF, DEFAULT_CUSTOM_LOW_CUTOFF),
            ): vol.All(vol.Coerce(float), vol.Range(min=CUSTOM_LOW_CUTOFF_MIN, max=CUSTOM_HIGH_CUTOFF_MAX)),
            vol.Required(
                CONF_CUSTOM_HIGH_CUTOFF,
                default=defaults.get(CONF_CUSTOM_HIGH_CUTOFF, DEFAULT_CUSTOM_HIGH_CUTOFF),
            ): vol.All(vol.Coerce(float), vol.Range(min=CUSTOM_LOW_CUTOFF_MIN, max=CUSTOM_HIGH_CUTOFF_MAX)),
        }
    )


def _custom_defaults(params: Mapping[str, Any] | None = None) -> dict[str, float]:
    params = params or {}
    return {
        CONF_CUSTOM_SLOPE: float(params.get(CONF_CUSTOM_SLOPE, DEFAULT_CUSTOM_SLOPE)),
        CONF_CUSTOM_LOW_CUTOFF: float(params.get(CONF_CUSTOM_LOW_CUTOFF, DEFAULT_CUSTOM_LOW_CUTOFF)),
        CONF_CUSTOM_HIGH_CUTOFF: float(params.get(CONF_CUSTOM_HIGH_CUTOFF, DEFAULT_CUSTOM_HIGH_CUTOFF)),
    }


def _profile_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    seed_default = ""
    raw_seed = defaults.get(CONF_SEED)
    if isinstance(raw_seed, (str, int)):
        seed_default = raw_seed
    return vol.Schema(
        {
            vol.Required(CONF_PROFILE_NAME, default=defaults.get(CONF_PROFILE_NAME, DEFAULT_PROFILE_NAME)): str,
            vol.Required(CONF_PROFILE_TYPE, default=defaults.get(CONF_PROFILE_TYPE, DEFAULT_PROFILE_TYPE)): vol.In(PROFILE_TYPES),
            vol.Required(CONF_VOLUME, default=defaults.get(CONF_VOLUME, DEFAULT_VOLUME)): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
            vol.Optional(CONF_SEED, default=seed_default): str,
        }
    )


def _profile_from_user_input(user_input: Mapping[str, Any]) -> dict[str, Any]:
    profile = {
        CONF_PROFILE_NAME: user_input[CONF_PROFILE_NAME],
        CONF_PROFILE_TYPE: user_input[CONF_PROFILE_TYPE],
        CONF_PROFILE_PARAMETERS: {
            CONF_VOLUME: user_input[CONF_VOLUME],
        },
    }
    seed = user_input.get(CONF_SEED)
    if seed not in (None, ""):
        profile[CONF_PROFILE_PARAMETERS][CONF_SEED] = seed
    if profile[CONF_PROFILE_TYPE] == "custom":
        slope = float(user_input.get(CONF_CUSTOM_SLOPE, DEFAULT_CUSTOM_SLOPE))
        low = float(user_input.get(CONF_CUSTOM_LOW_CUTOFF, DEFAULT_CUSTOM_LOW_CUTOFF))
        high = float(user_input.get(CONF_CUSTOM_HIGH_CUTOFF, DEFAULT_CUSTOM_HIGH_CUTOFF))
        profile[CONF_PROFILE_PARAMETERS][CONF_CUSTOM_SLOPE] = slope
        profile[CONF_PROFILE_PARAMETERS][CONF_CUSTOM_LOW_CUTOFF] = low
        profile[CONF_PROFILE_PARAMETERS][CONF_CUSTOM_HIGH_CUTOFF] = high
    else:
        profile[CONF_PROFILE_PARAMETERS].pop(CONF_CUSTOM_SLOPE, None)
        profile[CONF_PROFILE_PARAMETERS].pop(CONF_CUSTOM_LOW_CUTOFF, None)
        profile[CONF_PROFILE_PARAMETERS].pop(CONF_CUSTOM_HIGH_CUTOFF, None)
    cleaned = coerce_profile(profile)
    cleaned[CONF_PROFILE_NAME] = profile[CONF_PROFILE_NAME]
    return cleaned


class NoiseGeneratorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Noise Generator config flow."""

    VERSION = 1

    def __init__(self) -> None:
        super().__init__()
        self._pending_profile_base: dict[str, Any] | None = None
        self._pending_custom_defaults: dict[str, float] | None = None

    async def async_step_user(self, user_input: Mapping[str, Any] | None = None):
        """Configure the integration via the UI."""

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}

        if user_input is not None:
            profile_type = user_input[CONF_PROFILE_TYPE]
            if profile_type == "custom":
                self._pending_profile_base = dict(user_input)
                self._pending_custom_defaults = _custom_defaults()
                return await self.async_step_user_custom()
            profile = _profile_from_user_input(user_input)
            return self.async_create_entry(
                title="Noise Generator",
                data={CONF_PROFILES: [profile]},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_profile_schema(),
            errors=errors,
        )

    async def async_step_user_custom(self, user_input: Mapping[str, Any] | None = None):
        """Collect custom noise parameters for the first profile."""

        if not self._pending_profile_base:
            return await self.async_step_user()

        errors: dict[str, str] = {}

        if user_input is not None:
            merged = {**self._pending_profile_base, **user_input}
            profile = _profile_from_user_input(merged)
            self._pending_profile_base = None
            self._pending_custom_defaults = None
            return self.async_create_entry(
                title="Noise Generator",
                data={CONF_PROFILES: [profile]},
            )

        return self.async_show_form(
            step_id="user_custom",
            data_schema=_custom_params_schema(self._pending_custom_defaults),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return NoiseGeneratorOptionsFlowHandler(config_entry)


class NoiseGeneratorOptionsFlowHandler(config_entries.OptionsFlow):
    """Manage options for the Noise Generator integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._profiles: list[dict[str, Any]] = []
        self._selected_index: int | None = None
        self._action: str | None = None
        self._pending_profile_base: dict[str, Any] | None = None
        self._pending_custom_defaults: dict[str, float] | None = None

    async def async_step_init(self, user_input: Mapping[str, Any] | None = None):
        self._profiles = [
            {
                CONF_PROFILE_NAME: profile.get(CONF_PROFILE_NAME),
                **coerce_profile(profile),
            }
            for profile in self._config_entry.options.get(
                CONF_PROFILES,
                self._config_entry.data.get(CONF_PROFILES, []),
            )
        ]
        self._selected_index = None
        self._action = None
        self._pending_profile_base = None
        self._pending_custom_defaults = None
        return await self.async_step_action()

    async def async_step_action(self, user_input: Mapping[str, Any] | None = None):
        errors: dict[str, str] = {}

        actions: dict[str, str] = {
            ACTION_ADD: "Add profile",
            ACTION_EDIT: "Edit profile",
            ACTION_REMOVE: "Remove profile",
            ACTION_FINISH: "Save changes",
        }
        if not self._profiles:
            actions.pop(ACTION_EDIT)
            actions.pop(ACTION_REMOVE)

        if user_input is not None:
            action = user_input[CONF_ACTION]
            if action == ACTION_ADD:
                self._action = ACTION_ADD
                self._selected_index = None
                return await self.async_step_profile()
            if action == ACTION_EDIT:
                self._action = ACTION_EDIT
                return await self.async_step_select_profile()
            if action == ACTION_REMOVE:
                self._action = ACTION_REMOVE
                return await self.async_step_select_profile()
            if action == ACTION_FINISH:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_PROFILES: self._profiles,
                    },
                )

        return self.async_show_form(
            step_id="action",
            data_schema=vol.Schema({vol.Required(CONF_ACTION): vol.In(actions)}),
            errors=errors,
        )

    async def async_step_profile(self, user_input: Mapping[str, Any] | None = None):
        errors: dict[str, str] = {}
        defaults: dict[str, Any] = {}
        custom_defaults = _custom_defaults()

        if self._action == ACTION_EDIT and self._selected_index is not None:
            params = self._profiles[self._selected_index][CONF_PROFILE_PARAMETERS]
            seed_default = params.get(CONF_SEED) or ""
            defaults = {
                CONF_PROFILE_NAME: self._profiles[self._selected_index][CONF_PROFILE_NAME],
                CONF_PROFILE_TYPE: self._profiles[self._selected_index][CONF_PROFILE_TYPE],
                CONF_VOLUME: params[CONF_VOLUME],
                CONF_SEED: seed_default,
            }
            custom_defaults = _custom_defaults(params)

        self._pending_profile_base = None
        self._pending_custom_defaults = custom_defaults

        if user_input is not None:
            name = user_input[CONF_PROFILE_NAME]
            lower_name = name.casefold()
            for idx, profile in enumerate(self._profiles):
                if idx == self._selected_index:
                    continue
                if profile[CONF_PROFILE_NAME].casefold() == lower_name:
                    errors[CONF_PROFILE_NAME] = "duplicate"
                    break

            if not errors:
                if user_input[CONF_PROFILE_TYPE] == "custom":
                    self._pending_profile_base = dict(user_input)
                    if self._action == ACTION_EDIT and self._selected_index is not None:
                        params = self._profiles[self._selected_index][CONF_PROFILE_PARAMETERS]
                        self._pending_custom_defaults = _custom_defaults(params)
                    else:
                        self._pending_custom_defaults = _custom_defaults()
                    return await self.async_step_profile_custom()
                profile = _profile_from_user_input(user_input)
                if self._action == ACTION_EDIT and self._selected_index is not None:
                    self._profiles[self._selected_index] = profile
                else:
                    self._profiles.append(profile)
                return await self.async_step_action()

        return self.async_show_form(
            step_id="profile",
            data_schema=_profile_schema(defaults),
            errors=errors,
        )

    async def async_step_profile_custom(self, user_input: Mapping[str, Any] | None = None):
        errors: dict[str, str] = {}

        if not self._pending_profile_base:
            return await self.async_step_profile()

        if user_input is not None:
            merged = {**self._pending_profile_base, **user_input}
            profile = _profile_from_user_input(merged)
            if self._action == ACTION_EDIT and self._selected_index is not None:
                self._profiles[self._selected_index] = profile
            else:
                self._profiles.append(profile)
            self._pending_profile_base = None
            self._pending_custom_defaults = None
            return await self.async_step_action()

        return self.async_show_form(
            step_id="profile_custom",
            data_schema=_custom_params_schema(self._pending_custom_defaults),
            errors=errors,
        )

    async def async_step_select_profile(self, user_input: Mapping[str, Any] | None = None):
        errors: dict[str, str] = {}
        options: list[dict[str, str]] = []
        for idx, profile in enumerate(self._profiles):
            name = profile.get(CONF_PROFILE_NAME) or f"Profile {idx + 1}"
            display = name.strip() or f"Profile {idx + 1}"
            options.append({"label": display, "value": str(idx)})

        if not options:
            return await self.async_step_action()

        if user_input is not None:
            try:
                self._selected_index = int(user_input[CONF_PROFILE_NAME])
            except (TypeError, ValueError):
                errors["base"] = "unknown"
            else:
                if self._action == ACTION_REMOVE:
                    self._profiles.pop(self._selected_index)
                    self._selected_index = None
                    return await self.async_step_action()
                return await self.async_step_profile()

        return self.async_show_form(
            step_id="select_profile",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROFILE_NAME): selector.selector(
                        {"select": {"options": options}}
                    )
                }
            ),
            errors=errors,
        )
