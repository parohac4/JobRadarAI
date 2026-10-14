import { FormEvent, useEffect, useState } from "react";
import { apiClient } from "../api";
import type { Profile } from "../types";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [skillsText, setSkillsText] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiClient.get<Profile>("/profile").then((p) => {
      setProfile(p);
      setSkillsText((p.skills || []).join(", "));
    });
  }, []);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (!profile) return;
    const skills = skillsText.split(",").map((s) => s.trim()).filter(Boolean);
    const updated = await apiClient.put<Profile>("/profile", { ...profile, skills });
    setProfile(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  if (!profile) return <p>Načítání profilu…</p>;

  return (
    <form className="grid" onSubmit={onSave}>
      <h1>Profesní profil</h1>
      <section className="card grid">
        <label>
          Shrnutí
          <textarea rows={4} value={profile.summary} onChange={(e) => setProfile({ ...profile, summary: e.target.value })} />
        </label>
        <label>
          Dovednosti (čárkou)
          <input value={skillsText} onChange={(e) => setSkillsText(e.target.value)} />
        </label>
        <p className="muted">Preference (JSON): {JSON.stringify(profile.preferences)}</p>
        <button className="btn" type="submit">Uložit profil</button>
        {saved && <span className="muted">Uloženo</span>}
      </section>
    </form>
  );
}
