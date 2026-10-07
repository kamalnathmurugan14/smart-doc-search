import { NavLink, Route, Routes } from "react-router-dom";
import { useTheme } from "./hooks/useTheme";
import { DuplicatesPage } from "./pages/DuplicatesPage";
import { ExplorerPage } from "./pages/ExplorerPage";
import { SearchPage } from "./pages/SearchPage";
import { SettingsPage } from "./pages/SettingsPage";

export default function App() {
  const [theme, toggle] = useTheme();
  return (
    <div className="layout">
      <nav className="sidebar" aria-label="Main">
        <h1>🔎 Smart Doc Search</h1>
        <NavLink to="/" end>
          Search
        </NavLink>
        <NavLink to="/explorer">Explorer</NavLink>
        <NavLink to="/duplicates">Duplicates</NavLink>
        <NavLink to="/settings">Settings</NavLink>
        <span className="spacer" />
        <button type="button" onClick={toggle} aria-label="Toggle theme">
          {theme === "dark" ? "☀ Light" : "🌙 Dark"}
        </button>
      </nav>
      <main className="main">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/explorer" element={<ExplorerPage />} />
          <Route path="/duplicates" element={<DuplicatesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
