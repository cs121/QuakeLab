from __future__ import annotations

from pathlib import Path

from core.models.domain import ValidationDiagnostic
from core.parsers.def_parser import EntityDef, parse_def_file, parse_fgd_file
from core.parsers.map_parser import parse_entities
from core.parsers.shader_parser import validate_shader
from core.services.settings_service import SettingsService

# Standard Quake 1 entity classnames (always valid even without a .def file)
_BUILTIN_CLASSNAMES = {
    "worldspawn", "info_player_start", "info_player_deathmatch",
    "info_player_coop", "info_player_start2", "info_intermission",
    "info_null", "info_notnull", "info_teleport_destination",
    "light", "light_fluoro", "light_fluorospark", "light_globe",
    "light_flame_large_yellow", "light_flame_small_yellow",
    "light_flame_small_white", "light_torch_small_walltorch",
    "func_door", "func_door_secret", "func_wall", "func_button",
    "func_train", "func_plat", "func_illusionary", "func_episodegate",
    "func_bossgate",
    "trigger_once", "trigger_multiple", "trigger_relay", "trigger_secret",
    "trigger_teleport", "trigger_changelevel", "trigger_setskill",
    "trigger_counter", "trigger_hurt", "trigger_push",
    "monster_army", "monster_dog", "monster_ogre", "monster_knight",
    "monster_zombie", "monster_wizard", "monster_demon1", "monster_shambler",
    "monster_boss", "monster_enforcer", "monster_hell_knight",
    "monster_shalrath", "monster_tarbaby", "monster_fish",
    "item_health", "item_armor1", "item_armor2", "item_armorInv",
    "item_shells", "item_spikes", "item_rockets", "item_cells",
    "item_artifact_invulnerability", "item_artifact_envirosuit",
    "item_artifact_invisibility", "item_artifact_super_damage",
    "item_key1", "item_key2", "item_sigil",
    "weapon_supershotgun", "weapon_nailgun", "weapon_supernailgun",
    "weapon_grenadelauncher", "weapon_rocketlauncher", "weapon_lightning",
    "misc_fireball", "misc_explobox", "misc_explobox2",
    "ambient_suck_wind", "ambient_drone", "ambient_flouro_buzz",
    "ambient_drip", "ambient_comp_hum", "ambient_thunder",
    "ambient_light_buzz", "ambient_swamp1", "ambient_swamp2",
    "path_corner", "trap_spikeshooter", "trap_shooter",
    "air_bubbles", "event_lightning",
}


class ValidationService:
    def __init__(self, settings: SettingsService) -> None:
        self.settings = settings
        self._entity_defs: dict[str, EntityDef] | None = None

    def validate_shader_file(self, file_path: Path) -> list[ValidationDiagnostic]:
        """Validate a .shader file and return diagnostics."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return [ValidationDiagnostic(
                file_path=str(file_path),
                line=0,
                severity="error",
                message=f"Could not read file: {file_path}",
            )]

        source_root = self.settings.source_root().resolve()
        return validate_shader(str(file_path), content, source_root)

    def validate_map_entities(self, file_path: Path) -> list[ValidationDiagnostic]:
        """Validate entities in a .map file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return [ValidationDiagnostic(
                file_path=str(file_path),
                line=0,
                severity="error",
                message=f"Could not read file: {file_path}",
            )]

        entities = parse_entities(content)
        known = self._load_known_classnames()
        diags: list[ValidationDiagnostic] = []

        for ent in entities:
            if not ent.classname:
                diags.append(ValidationDiagnostic(
                    file_path=str(file_path),
                    line=ent.line,
                    severity="error",
                    message="Entity missing 'classname' property",
                ))
                continue

            if known and ent.classname not in known:
                diags.append(ValidationDiagnostic(
                    file_path=str(file_path),
                    line=ent.line,
                    severity="warning",
                    message=f"Unknown entity classname: {ent.classname}",
                ))

            # Validate origin format for point entities
            origin = ent.properties.get("origin", "")
            if origin:
                parts = origin.split()
                if len(parts) != 3 or not all(_is_number(p) for p in parts):
                    diags.append(ValidationDiagnostic(
                        file_path=str(file_path),
                        line=ent.line,
                        severity="warning",
                        message=f"Invalid origin format: '{origin}' (expected 'x y z')",
                    ))

        return diags

    def _load_known_classnames(self) -> set[str]:
        """Load known classnames from entity def file or use builtins."""
        if self._entity_defs is not None:
            return set(self._entity_defs.keys()) | _BUILTIN_CLASSNAMES

        def_path_str = self.settings.get("entity_def_path", "")
        if def_path_str:
            def_path = Path(def_path_str)
            if def_path.exists():
                try:
                    if def_path.suffix.lower() == ".fgd":
                        self._entity_defs = parse_fgd_file(def_path)
                    else:
                        self._entity_defs = parse_def_file(def_path)
                    return set(self._entity_defs.keys()) | _BUILTIN_CLASSNAMES
                except OSError:
                    pass

        self._entity_defs = {}
        return _BUILTIN_CLASSNAMES


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False
