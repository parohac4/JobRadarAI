import { FormEvent, useEffect, useState } from "react";
import { apiClient, errorText } from "../api";
import type { Profile } from "../types";

const splitList = (text: string) => text.split(",").map((s) => s.trim()).filter(Boolean);
const joinList = (value: unknown) => (Array.isArray(value) ? value.join(", ") : "");
const toJson = (value: unknown) => JSON.stringify(value ?? [], null, 2);

function parseJsonList(label: string, text: string): Record<string, unknown>[] {
  let value: unknown;
  try {
    value = JSON.parse(text || "[]");
  } catch {
    throw new Error(`${label}: neplatný JSON`);
  }
  if (!Array.isArray(value) || !value.every((v) => v && typeof v === "object" && !Array.isArray(v))) {
    throw new Error(`${label}: očekává se seznam objektů, např. [{"role": "..."}]`);
  }
  return value as Record<string, unknown>[];
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [skillsText, setSkillsText] = useState("");
  const [regionsText, setRegionsText] = useState("");
  const [rolesText, setRolesText] = useState("");
  const [experienceText, setExperienceText] = useState("");
  const [educationText, setEducationText] = useState("");
  const [cvText, setCvText] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  function fill(p: Profile) {
    setProfile(p);
    setSkillsText((p.skills || []).join(", "));
    setRegionsText(joinList(p.preferences?.regions));
    setRolesText(joinList(p.preferences?.roles));
    setExperienceText(toJson(p.experience));
    setEducationText(toJson(p.education));
    setCvText(toJson(p.cv_versions));
  }

  useEffect(() => {
    apiClient.get<Profile>("/profile").then(fill).catch((err) => setError(errorText(err)));
  }, []);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (!profile) return;
    setError("");
    setStatus("");
    try {
      const payload = {
        summary: profile.summary,
        skills: splitList(skillsText),
        experience: parseJsonList("Zkušenosti", experienceText),
        education: parseJsonList("Vzdělání", educationText),
        cv_versions: parseJsonList("Verze CV", cvText),
        preferences: { ...profile.preferences, regions: splitList(regionsText), roles: splitList(rolesText) },
      };
      fill(await apiClient.put<Profile>("/profile", payload));
      setStatus("Uloženo");
    } catch (err) {
      setError(errorText(err));
    }
  }

  if (!profile) return error ? <p className="error" role="alert">{error}</p> : <p>Načítání profilu…</p>;

  return (
    <form className="grid" onSubmit={onSave}>
      <h1>Profesní profil</h1>
      <p className="muted">
        AI pracuje jen s tím, co je zde uvedeno – nic si nedomýšlí. Uvádějte pouze skutečné zkušenosti a kvalifikace.
      </p>
      <section className="card grid">
        <label>
          Shrnutí
          <textarea rows={4} value={profile.summary} onChange={(e) => setProfile({ ...profile, summary: e.target.value })} />
        </label>
        <label>
          Dovednosti (oddělené čárkou)
          <input value={skillsText} onChange={(e) => setSkillsText(e.target.value)} />
        </label>
        <label>
          Preferované lokality (čárkou, např. Jihočeský kraj, remote)
          <input value={regionsText} onChange={(e) => setRegionsText(e.target.value)} />
        </label>
        <label>
          Hledané role (čárkou)
          <input value={rolesText} onChange={(e) => setRolesText(e.target.value)} />
        </label>
      </section>
      <section className="card grid">
        <h2>Strukturovaná data (JSON)</h2>
        <label>
          Zkušenosti
          <textarea rows={6} spellCheck={false} value={experienceText} onChange={(e) => setExperienceText(e.target.value)} />
        </label>
        <label>
          Vzdělání
          <textarea rows={4} spellCheck={false} value={educationText} onChange={(e) => setEducationText(e.target.value)} />
        </label>
        <label>
          Verze CV (první je doporučená výchozí)
          <textarea rows={4} spellCheck={false} value={cvText} onChange={(e) => setCvText(e.target.value)} />
        </label>
      </section>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="row">
        <button className="btn" type="submit">Uložit profil</button>
        {status && <span className="muted" role="status">{status}</span>}
      </div>
    </form>
  );
}
