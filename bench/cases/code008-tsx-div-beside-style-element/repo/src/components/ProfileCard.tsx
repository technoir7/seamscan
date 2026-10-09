"use client";

type Profile = { id: string; name: string; accent: string; bioHtml: string };

export function ProfileCard({ profile }: { profile: Profile }) {
  const css = `
    #profile-${profile.id} h2 { color: ${profile.accent}; }
    #profile-${profile.id} a { text-decoration: underline; }
  `;

  return (
    <article id={`profile-${profile.id}`} className="rounded-lg border p-4">
      <style dangerouslySetInnerHTML={{ __html: css }} />
      <h2 className="text-lg font-semibold">{profile.name}</h2>
      <div
        className="prose mt-2"
        // The bio comes from the profile editor's rich-text field.
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: profile.bioHtml }}
      />
    </article>
  );
}
