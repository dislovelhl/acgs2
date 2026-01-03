/**
 * SourceSelectionStep Component
 *
 * First step of the import wizard - allows users to select their data source.
 * Features:
 * - Interactive cards for JIRA, ServiceNow, GitHub, and GitLab
 * - Visual feedback for selected source
 * - Source descriptions and icons
 * - Hover and selection states
 */

import { useCallback } from "react";
import {
  CheckCircle2,
  Database,
  FileText,
  GitBranch,
  GitMerge,
} from "lucide-react";
import type { ImportConfig, SourceTool } from "./ImportWizard";

/** Props for SourceSelectionStep component */
export interface SourceSelectionStepProps {
  /** Current import configuration */
  config: ImportConfig;
  /** Callback to update import configuration */
  onConfigUpdate: (updates: Partial<ImportConfig>) => void;
}

/** Source tool metadata for display */
interface SourceToolInfo {
  /** Tool identifier */
  id: SourceTool;
  /** Display name */
  name: string;
  /** Brief description */
  description: string;
  /** Icon component */
  icon: React.ComponentType<{ className?: string }>;
  /** Icon background color class */
  iconBgColor: string;
  /** Icon color class */
  iconColor: string;
}

/** Available source tools with metadata */
const SOURCE_TOOLS: SourceToolInfo[] = [
  {
    id: "jira",
    name: "JIRA",
    description: "Import issues, projects, and workflows from Atlassian JIRA",
    icon: FileText,
    iconBgColor: "bg-blue-100",
    iconColor: "text-blue-600",
  },
  {
    id: "servicenow",
    name: "ServiceNow",
    description: "Import incidents, tasks, and change requests from ServiceNow",
    icon: Database,
    iconBgColor: "bg-green-100",
    iconColor: "text-green-600",
  },
  {
    id: "github",
    name: "GitHub",
    description: "Import issues, pull requests, and projects from GitHub",
    icon: GitBranch,
    iconBgColor: "bg-gray-100",
    iconColor: "text-gray-700",
  },
  {
    id: "gitlab",
    name: "GitLab",
    description: "Import issues, merge requests, and projects from GitLab",
    icon: GitMerge,
    iconBgColor: "bg-orange-100",
    iconColor: "text-orange-600",
  },
];

/**
 * SourceToolCard - Individual card for a source tool
 */
interface SourceToolCardProps {
  tool: SourceToolInfo;
  isSelected: boolean;
  onSelect: (toolId: SourceTool) => void;
}

function SourceToolCard({
  tool,
  isSelected,
  onSelect,
}: SourceToolCardProps): JSX.Element {
  const Icon = tool.icon;

  return (
    <button
      onClick={() => onSelect(tool.id)}
      className={`
        relative w-full p-6 rounded-lg border-2 transition-all duration-200 text-left
        ${
          isSelected
            ? "border-blue-500 bg-blue-50 shadow-md"
            : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm"
        }
      `}
      aria-pressed={isSelected}
      aria-label={`Select ${tool.name} as data source`}
    >
      {/* Selection indicator */}
      {isSelected && (
        <div className="absolute top-4 right-4">
          <CheckCircle2 className="w-6 h-6 text-blue-600" />
        </div>
      )}

      {/* Icon */}
      <div
        className={`
          inline-flex items-center justify-center w-12 h-12 rounded-lg mb-4
          ${tool.iconBgColor}
        `}
      >
        <Icon className={`w-6 h-6 ${tool.iconColor}`} />
      </div>

      {/* Content */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          {tool.name}
        </h3>
        <p className="text-sm text-gray-600 leading-relaxed">
          {tool.description}
        </p>
      </div>
    </button>
  );
}

/**
 * SourceSelectionStep - Source tool selection step
 *
 * Displays cards for each available data source (JIRA, ServiceNow, GitHub, GitLab).
 * User selects one source to proceed with the import process.
 */
export function SourceSelectionStep({
  config,
  onConfigUpdate,
}: SourceSelectionStepProps): JSX.Element {
  /**
   * Handle source tool selection
   */
  const handleSelectTool = useCallback(
    (toolId: SourceTool) => {
      onConfigUpdate({ sourceTool: toolId });
    },
    [onConfigUpdate]
  );

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Choose Your Data Source
        </h2>
        <p className="text-gray-600">
          Select the project management tool you want to import data from.
          You'll configure authentication details in the next step.
        </p>
      </div>

      {/* Source tool cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SOURCE_TOOLS.map((tool) => (
          <SourceToolCard
            key={tool.id}
            tool={tool}
            isSelected={config.sourceTool === tool.id}
            onSelect={handleSelectTool}
          />
        ))}
      </div>

      {/* Help text */}
      {config.sourceTool && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-900">
            <strong className="font-semibold">Next step:</strong> You'll need
            to provide authentication credentials for{" "}
            {SOURCE_TOOLS.find((t) => t.id === config.sourceTool)?.name}. Make
            sure you have your API token or credentials ready.
          </p>
        </div>
      )}
    </div>
  );
}
