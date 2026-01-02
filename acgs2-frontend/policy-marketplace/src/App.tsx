/**
 * ACGS-2 Policy Marketplace App
 * Constitutional Hash: 018-policy-marketplace
 *
 * Main application component with routing
 */

import { BrowserRouter, Routes, Route } from "react-router-dom";

function HomePage(): JSX.Element {
  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">
            ACGS-2 Policy Marketplace
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            Discover, share, and manage governance policy templates
          </p>
        </div>
      </header>
      <main>
        <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            <div className="border-4 border-dashed border-gray-200 rounded-lg p-8 text-center">
              <h2 className="text-xl font-semibold text-gray-700 mb-4">
                Welcome to the Policy Marketplace
              </h2>
              <p className="text-gray-500 mb-6">
                Browse verified community templates or create your own
                organization-private library.
              </p>
              <div className="flex justify-center gap-4">
                <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
                  Browse Templates
                </button>
                <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors">
                  Upload Template
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function App(): JSX.Element {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
