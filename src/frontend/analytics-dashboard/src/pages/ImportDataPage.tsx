/**
 * ImportDataPage Component
 *
 * Main page for the data import wizard workflow.
 * Features:
 * - Multi-step import wizard for external tools
 * - Help panel with migration guides
 * - Navigation back to dashboard
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { HelpCircle } from "lucide-react";
import { ImportWizard } from "../components/ImportWizard/ImportWizard";
import { HelpPanel } from "../components/ImportWizard/HelpPanel";

/**
 * ImportDataPage - Main page for data import workflow
 *
 * Provides:
 * - Import wizard for selecting source, configuring, and importing data
 * - Contextual help panel with migration guides
 * - Navigation callbacks for completion/cancellation
 */
export function ImportDataPage(): JSX.Element {
  const navigate = useNavigate();
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  /**
   * Handle successful import completion
   * Navigate back to dashboard
   */
  const handleComplete = () => {
    navigate("/");
  };

  /**
   * Handle import cancellation
   * Navigate back to dashboard
   */
  const handleCancel = () => {
    navigate("/");
  };

  return (
    <div className="relative">
      {/* Help button - fixed position */}
      <button
        onClick={() => setIsHelpOpen(true)}
        className="fixed bottom-6 right-6 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition-colors z-30"
        aria-label="Open help panel"
        title="Need help?"
      >
        <HelpCircle className="w-6 h-6" />
      </button>

      {/* Import Wizard */}
      <ImportWizard onComplete={handleComplete} onCancel={handleCancel} />

      {/* Help Panel */}
      <HelpPanel
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
        importContext={undefined}
      />
    </div>
  );
}
