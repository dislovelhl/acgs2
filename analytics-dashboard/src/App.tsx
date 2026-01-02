/**
 * ACGS-2 Analytics Dashboard App
 *
 * Main application component for advanced analytics and insights
 */

import { InsightWidget } from "./components/widgets/InsightWidget";

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
        {/* Dashboard Grid - widgets will be arranged via react-grid-layout in DashboardGrid.tsx */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* AI Insights Widget */}
          <div className="h-96">
            <InsightWidget />
          </div>

          {/* Placeholder for additional widgets */}
          <div className="h-96 rounded-lg border border-dashed border-gray-300 bg-white p-6">
            <p className="text-center text-gray-500">
              Additional widgets will be implemented here
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
