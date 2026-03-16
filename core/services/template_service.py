from __future__ import annotations

from pathlib import Path

_TEMPLATES: dict[str, dict[str, str]] = {
    "Empty Mod": {
        "src/progs.src": (
            "progs.dat\n"
            "\n"
            "defs.qc\n"
            "world.qc\n"
        ),
        "src/defs.qc": (
            "// Entity field definitions\n"
            "\n"
            "entity self;\n"
            "entity other;\n"
            "entity world;\n"
            "\n"
            "void() main;\n"
            "void() StartFrame;\n"
        ),
        "src/world.qc": (
            "void() worldspawn =\n"
            "{\n"
            "};\n"
            "\n"
            "void() main =\n"
            "{\n"
            "};\n"
            "\n"
            "void() StartFrame =\n"
            "{\n"
            "};\n"
        ),
        "src/maps/.gitkeep": "",
        "src/gfx/.gitkeep": "",
        "src/sound/.gitkeep": "",
        "readme.txt": "My Quake Mod\n============\n\nDescription goes here.\n",
    },
    "Starter Mod": {
        "src/progs.src": (
            "progs.dat\n"
            "\n"
            "defs.qc\n"
            "subs.qc\n"
            "combat.qc\n"
            "world.qc\n"
            "items.qc\n"
        ),
        "src/defs.qc": (
            "// Standard Quake entity field definitions\n"
            "\n"
            "entity self;\n"
            "entity other;\n"
            "entity world;\n"
            "\n"
            "float time;\n"
            "float frametime;\n"
            "float force_retouch;\n"
            "string mapname;\n"
            "\n"
            ".string classname;\n"
            ".string model;\n"
            ".float health;\n"
            ".vector origin;\n"
            ".vector angles;\n"
            ".float movetype;\n"
            ".float solid;\n"
            ".string targetname;\n"
            ".string target;\n"
            "\n"
            "float MOVETYPE_NONE = 0;\n"
            "float MOVETYPE_WALK = 3;\n"
            "float MOVETYPE_STEP = 4;\n"
            "float MOVETYPE_FLY = 5;\n"
            "float MOVETYPE_TOSS = 6;\n"
            "float MOVETYPE_NOCLIP = 8;\n"
            "\n"
            "float SOLID_NOT = 0;\n"
            "float SOLID_TRIGGER = 1;\n"
            "float SOLID_BBOX = 2;\n"
            "float SOLID_BSP = 4;\n"
            "\n"
            "void() main;\n"
            "void() StartFrame;\n"
            "void() SUB_Remove;\n"
        ),
        "src/subs.qc": (
            "void() SUB_Remove =\n"
            "{\n"
            "    remove(self);\n"
            "};\n"
        ),
        "src/combat.qc": (
            "// Combat utilities\n"
            "// Add damage, kill tracking, etc.\n"
        ),
        "src/world.qc": (
            "void() worldspawn =\n"
            "{\n"
            '    precache_model("progs/player.mdl");\n'
            "};\n"
            "\n"
            "void() main =\n"
            "{\n"
            '    dprint("Mod initialized\\n");\n'
            "};\n"
            "\n"
            "void() StartFrame =\n"
            "{\n"
            "};\n"
        ),
        "src/items.qc": (
            "// Item pickup logic\n"
            "// Add custom items here.\n"
        ),
        "src/maps/.gitkeep": "",
        "src/gfx/.gitkeep": "",
        "src/sound/.gitkeep": "",
        "src/progs/.gitkeep": "",
        "readme.txt": (
            "My Quake Mod\n"
            "============\n"
            "\n"
            "A starter Quake mod with basic project structure.\n"
            "\n"
            "Building:\n"
            "  1. Set QC compiler path in QuakeLab Settings\n"
            "  2. Build > Rebuild All\n"
            "\n"
            "Playing:\n"
            "  1. Set engine path in Settings\n"
            "  2. Click Play\n"
        ),
    },
}


class TemplateService:
    def available_templates(self) -> list[str]:
        return list(_TEMPLATES.keys())

    def create_from_template(self, template_name: str, target_dir: Path) -> list[Path]:
        """Scaffold a project from a template. Returns list of created files."""
        if template_name not in _TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}")

        files = _TEMPLATES[template_name]
        created: list[Path] = []

        for rel_path, content in files.items():
            full_path = target_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            created.append(full_path)

        return created
