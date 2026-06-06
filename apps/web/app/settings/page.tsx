import { Bell, Database, MonitorCog, SlidersHorizontal } from "lucide-react";

export default function SettingsPage() {
  return (
    <>
      <div className="topline">
        <div>
          <p className="eyebrow">Operating policy</p>
          <h2>Settings</h2>
        </div>
      </div>
      <section className="metric-grid">
        <Setting icon={<SlidersHorizontal />} title="Autonomy" body="Auto-fill high-confidence business fields; always pause for personal, legal, access, submission, endorsement, and payment boundaries." />
        <Setting icon={<Bell />} title="Notifications" body="In-app requests are active for MVP. Email routing is planned after auth and team access." />
        <Setting icon={<Database />} title="Retention" body="Documents are short-lived by default. Extracted facts retain confidence, source, and sensitivity labels." />
        <Setting icon={<MonitorCog />} title="Computer Use" body="Live safe-browser runs use OpenAI computer use with an isolated Playwright context. Access, credential, CAPTCHA, declaration, endorsement, payment, and submit walls always become human handoffs." />
      </section>
    </>
  );
}

function Setting({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="panel metric setting-card">
      <div className="section-heading">
        <h3>{title}</h3>
        {icon}
      </div>
      <p className="muted">{body}</p>
    </div>
  );
}
