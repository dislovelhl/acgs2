/**
 * ACGS-2 Analytics Dashboard App
 *
 * Main application component for advanced analytics and insights.
 * Uses react-grid-layout for customizable, draggable widget layouts
 * with localStorage persistence.
 */

import { DashboardGrid } from "./layouts/DashboardGrid";
import { QueryInterface } from "./components/QueryInterface";

function App(): JSX.Element {
  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">
            ACGS-2 Analytics Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            AI-Powered Governance Insights and Predictive Analytics
          </p>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {/* Natural Language Query Interface */}
        <div className="mb-6">
          <QueryInterface />
        </div>

        {/* Dashboard Grid with draggable widgets */}
        <DashboardGrid />
      </main>
    </div>
  );
}

export default App;
