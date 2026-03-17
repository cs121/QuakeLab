from __future__ import annotations

from dataclasses import dataclass

from core.services.settings_service import SettingsService
from infrastructure.db.database import Database


@dataclass(slots=True)
class BuildProfile:
    id: int
    name: str
    qc_args: str
    qbsp_args: str
    vis_args: str
    light_args: str
    map_build_mode: str


class BuildProfileService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_profiles(self) -> list[BuildProfile]:
        rows = self.db.query(
            "SELECT id, name, qc_args, qbsp_args, vis_args, light_args, map_build_mode "
            "FROM build_profiles ORDER BY name"
        )
        return [BuildProfile(id=r[0], name=r[1], qc_args=r[2], qbsp_args=r[3],
                             vis_args=r[4], light_args=r[5], map_build_mode=r[6])
                for r in rows]

    def get_profile(self, name: str) -> BuildProfile | None:
        rows = self.db.query(
            "SELECT id, name, qc_args, qbsp_args, vis_args, light_args, map_build_mode "
            "FROM build_profiles WHERE name = ?", (name,)
        )
        if not rows:
            return None
        r = rows[0]
        return BuildProfile(id=r[0], name=r[1], qc_args=r[2], qbsp_args=r[3],
                            vis_args=r[4], light_args=r[5], map_build_mode=r[6])

    def save_profile(self, profile: BuildProfile) -> None:
        self.db.execute(
            "INSERT INTO build_profiles(name, qc_args, qbsp_args, vis_args, light_args, map_build_mode) "
            "VALUES(?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET qc_args=excluded.qc_args, qbsp_args=excluded.qbsp_args, "
            "vis_args=excluded.vis_args, light_args=excluded.light_args, map_build_mode=excluded.map_build_mode",
            (profile.name, profile.qc_args, profile.qbsp_args, profile.vis_args,
             profile.light_args, profile.map_build_mode),
        )

    def delete_profile(self, name: str) -> None:
        self.db.execute("DELETE FROM build_profiles WHERE name = ?", (name,))

    def apply_profile(self, profile: BuildProfile, settings: SettingsService) -> None:
        """Write a profile's arguments into the settings service."""
        settings.set("qc_args", profile.qc_args)
        settings.set("qbsp_args", profile.qbsp_args)
        settings.set("vis_args", profile.vis_args)
        settings.set("light_args", profile.light_args)
        settings.set("map_build_mode", profile.map_build_mode)
        settings.set("active_build_profile", profile.name)
