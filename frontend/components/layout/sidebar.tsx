import Link from "next/link";

const links = [
  { href: "/", label: "Dashboard", icon: "01" },
  { href: "/tickets", label: "Tickets", icon: "02" },
  { href: "/knowledge-base", label: "Knowledge Base", icon: "03" },
  { href: "/evaluation", label: "Evaluation", icon: "04" },
];

export function Sidebar({ pathname }: { pathname: string }) {
  return <aside className="sidebar">
    <div className="brand"><span className="brand-mark">CD</span><div><div className="brand-name">CloudDesk</div><div className="brand-subtitle">Support workspace</div></div></div>
    <nav aria-label="Primary navigation"><p className="nav-label">Workspace</p><div className="nav-list">{links.map((link) => {
      const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
      return <Link className={`nav-link${active ? " nav-link-active" : ""}`} href={link.href} key={link.href} aria-current={active ? "page" : undefined}><span className="nav-icon">{link.icon}</span>{link.label}</Link>;
    })}</div></nav>
    <div className="sidebar-footer">Internal operations<br />CloudDesk v0.1</div>
  </aside>;
}