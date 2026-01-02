/**
 * ACGS-2 Policy Marketplace App
 * Constitutional Hash: 018-policy-marketplace
 *
 * Main application component with routing
 */

import { BrowserRouter, Routes, Route, Link, useNavigate } from "react-router-dom";
import { TemplateList } from "@components/TemplateList";
import { TemplateDetail } from "@components/TemplateDetail";
import type { TemplateListItem } from "@types/template";

function Header(): JSX.Element {
  return (
    <header className="bg-white shadow">
      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <div>
            <Link to="/" className="hover:opacity-80 transition-opacity">
              <h1 className="text-3xl font-bold text-gray-900">
                ACGS-2 Policy Marketplace
              </h1>
            </Link>
            <p className="mt-1 text-sm text-gray-600">
              Discover, share, and manage governance policy templates
            </p>
          </div>
          <nav className="flex items-center gap-4">
            <Link
              to="/templates"
              className="px-4 py-2 text-gray-700 hover:text-blue-600 transition-colors"
            >
              Browse
            </Link>
            <Link
              to="/upload"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Upload Template
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}

function HomePage(): JSX.Element {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-100">
      <Header />
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
                <button
                  onClick={() => navigate("/templates")}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Browse Templates
                </button>
                <button
                  onClick={() => navigate("/upload")}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
                >
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

function TemplatesPage(): JSX.Element {
  const navigate = useNavigate();

  const handleTemplateSelect = (template: TemplateListItem) => {
    navigate(`/templates/${template.id}`);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Header />
      <main>
        <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <TemplateList onTemplateSelect={handleTemplateSelect} />
        </div>
      </main>
    </div>
  );
}

function TemplateDetailPage(): JSX.Element {
  return (
    <div className="min-h-screen bg-gray-100">
      <Header />
      <main>
        <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <TemplateDetail />
        </div>
      </main>
    </div>
  );
}

function UploadPage(): JSX.Element {
  return (
    <div className="min-h-screen bg-gray-100">
      <Header />
      <main>
        <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm text-center">
            <p className="text-gray-500">Upload template form coming soon...</p>
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
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/templates/:id" element={<TemplateDetailPage />} />
        <Route path="/template/:id" element={<TemplateDetailPage />} />
        <Route path="/upload" element={<UploadPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
