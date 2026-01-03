/**
 * ImportWizard Component
 *
 * Multi-step wizard for importing data from external project management tools.
 * Features:
 * - Source tool selection (JIRA, ServiceNow, GitHub, GitLab)
 * - Authentication configuration
 * - Data preview before import
 * - Real-time progress tracking
 * - Step navigation and state management
 */

import { useCallback, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Circle,
  X,
} from "lucide-react";

/** Available source tools for data import */
export type SourceTool = "jira" | "servicenow" | "github" | "gitlab";

/** Import configuration state shared across steps */
export interface ImportConfig {
  /** Selected source tool */
  sourceTool?: SourceTool;
  /** Authentication credentials (tool-specific) */
  credentials?: {
    baseUrl?: string;
    apiToken?: string;
    username?: string;
    password?: string;
    projectKey?: string;
    repository?: string;
    instance?: string;
  };
  /** Preview data from the source */
  previewData?: {
    items: Array<{
      id: string;
      title: string;
      status: string;
      assignee?: string;
      createdAt: string;
    }>;
    totalCount: number;
  };
  /** Job ID for tracking import progress */
  jobId?: string;
}

/** Individual step configuration */
interface WizardStep {
  /** Step display name */
  title: string;
  /** Step description */
  description: string;
  /** Whether this step can be skipped */
  optional?: boolean;
}

/** Props for ImportWizard component */
export interface ImportWizardProps {
  /** Callback when import completes successfully */
  onComplete: () => void;
  /** Callback when user cancels the wizard */
  onCancel: () => void;
}

/** Wizard steps configuration */
const WIZARD_STEPS: WizardStep[] = [
  {
    title: "Choose Source",
    description: "Select the tool you want to import data from",
  },
  {
    title: "Configure",
    description: "Provide authentication credentials",
  },
  {
    title: "Preview",
    description: "Review data before importing",
  },
  {
    title: "Import",
    description: "Track import progress",
  },
];

/**
 * StepIndicator - Visual progress indicator for wizard steps
 */
interface StepIndicatorProps {
  steps: WizardStep[];
  currentStep: number;
}

function StepIndicator({
  steps,
  currentStep,
}: StepIndicatorProps): JSX.Element {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;

          return (
            <div key={step.title} className="flex items-center flex-1">
              {/* Step circle */}
              <div className="flex flex-col items-center">
                <div
                  className={`
                    flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors
                    ${
                      isCompleted
                        ? "bg-green-500 border-green-500"
                        : isCurrent
                          ? "bg-blue-500 border-blue-500"
                          : "bg-white border-gray-300"
                    }
                  `}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="w-6 h-6 text-white" />
                  ) : (
                    <Circle
                      className={`w-6 h-6 ${isCurrent ? "text-white" : "text-gray-400"}`}
                    />
                  )}
                </div>

                {/* Step label */}
                <div className="mt-2 text-center">
                  <div
                    className={`text-sm font-medium ${
                      isCurrent
                        ? "text-blue-600"
                        : isCompleted
                          ? "text-green-600"
                          : "text-gray-500"
                    }`}
                  >
                    {step.title}
                  </div>
                  <div className="text-xs text-gray-500 mt-1 max-w-[120px]">
                    {step.description}
                  </div>
                </div>
              </div>

              {/* Connector line (except for last step) */}
              {index < steps.length - 1 && (
                <div
                  className={`
                    flex-1 h-0.5 mx-4 transition-colors
                    ${isCompleted ? "bg-green-500" : "bg-gray-300"}
                  `}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * ImportWizard - Multi-step data import wizard
 *
 * Manages the complete import workflow:
 * 1. Source selection
 * 2. Authentication configuration
 * 3. Data preview
 * 4. Import execution and progress tracking
 */
export function ImportWizard({
  onComplete,
  onCancel,
}: ImportWizardProps): JSX.Element {
  const [currentStep, setCurrentStep] = useState(0);
  const [importConfig, setImportConfig] = useState<ImportConfig>({});

  /**
   * Navigate to the next step
   */
  const handleNext = useCallback(() => {
    if (currentStep < WIZARD_STEPS.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      // Last step - trigger completion
      onComplete();
    }
  }, [currentStep, onComplete]);

  /**
   * Navigate to the previous step
   */
  const handleBack = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  }, [currentStep]);

  /**
   * Update import configuration
   * TODO: Pass to step components when implemented
   */
  const updateConfig = useCallback((updates: Partial<ImportConfig>) => {
    setImportConfig((prev) => ({ ...prev, ...updates }));
  }, []);

  // Suppress unused warning - will be used when step components are integrated
  void updateConfig;

  /**
   * Check if current step is valid and can proceed
   */
  const canProceed = useCallback((): boolean => {
    switch (currentStep) {
      case 0: // Source selection
        return !!importConfig.sourceTool;
      case 1: // Configuration
        return !!importConfig.credentials;
      case 2: // Preview
        return !!importConfig.previewData;
      case 3: // Progress
        return !!importConfig.jobId;
      default:
        return false;
    }
  }, [currentStep, importConfig]);

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Import Your Data
              </h1>
              <p className="text-gray-600 mt-1">
                Migrate data from your existing project management tools
              </p>
            </div>
            <button
              onClick={onCancel}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Cancel import"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Step indicator */}
          <StepIndicator steps={WIZARD_STEPS} currentStep={currentStep} />
        </div>

        {/* Step content */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="min-h-[400px]">
            {/* Placeholder for step components - will be implemented in subsequent subtasks */}
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  {WIZARD_STEPS[currentStep].title}
                </h2>
                <p className="text-gray-600">
                  {WIZARD_STEPS[currentStep].description}
                </p>
                <div className="mt-4 text-sm text-gray-500">
                  Step {currentStep + 1} of {WIZARD_STEPS.length}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation buttons */}
        <div className="flex items-center justify-between">
          <button
            onClick={handleBack}
            disabled={currentStep === 0}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors
              ${
                currentStep === 0
                  ? "text-gray-400 cursor-not-allowed"
                  : "text-gray-700 hover:bg-gray-100"
              }
            `}
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>

          <div className="flex gap-3">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleNext}
              disabled={!canProceed()}
              className={`
                flex items-center gap-2 px-6 py-2 rounded-lg font-medium transition-colors
                ${
                  canProceed()
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "bg-gray-300 text-gray-500 cursor-not-allowed"
                }
              `}
            >
              {currentStep === WIZARD_STEPS.length - 1 ? "Finish" : "Next"}
              {currentStep !== WIZARD_STEPS.length - 1 && (
                <ArrowRight className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
