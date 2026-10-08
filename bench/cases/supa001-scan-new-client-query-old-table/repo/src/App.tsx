import { Projects } from "./components/Projects";
import { FeedbackWidget } from "./components/FeedbackWidget";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Projects />
      <FeedbackWidget />
    </div>
  );
}
