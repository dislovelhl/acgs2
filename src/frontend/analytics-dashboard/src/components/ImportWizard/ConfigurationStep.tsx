/**
 * ConfigurationStep Component
 *
 * Second step of the import wizard - authentication and configuration.
 * Features:
 * - Dynamic form fields based on selected source tool
 * - Credential input with validation
 * - Test connection functionality
 * - Loading and error states
 * - Secure password input
 */

import { useCallback, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Eye,
  EyeOff,
  HelpCircle,
  Key,
  Link as LinkIcon,
  Loader2,
  User,
} from "lucide-react";
import type { ImportConfig, SourceTool } from "./ImportWizard";

/** Props for ConfigurationStep component */
export interface ConfigurationStepProps {
  /** Current import configuration */
  config: ImportConfig;
  /** Callback to update import configuration */
  onConfigUpdate: (updates: Partial<ImportConfig>) => void;
}

/** Connection test state */
type ConnectionState = "idle" | "testing" | "success" | "error";

/** Form field errors */
interface FormErrors {
  [key: string]: string;
}

/**
 * Gets the display name for a source tool
 */
function getSourceToolName(tool: SourceTool | undefined): string {
  switch (tool) {
    case "jira":
      return "JIRA";
    case "servicenow":
      return "ServiceNow";
    case "github":
      return "GitHub";
    case "gitlab":
      return "GitLab";
    default:
      return "Unknown";
  }
}

/**
 * Validates required fields based on source tool
 */
function validateCredentials(
  tool: SourceTool | undefined,
  credentials: ImportConfig["credentials"]
): FormErrors {
  const errors: FormErrors = {};

  if (!tool || !credentials) {
    return errors;
  }

  switch (tool) {
    case "jira":
      if (!credentials.baseUrl?.trim()) {
        errors.baseUrl = "JIRA URL is required";
      } else if (!credentials.baseUrl.startsWith("https://")) {
        errors.baseUrl = "URL must start with https://";
      }
      if (!credentials.username?.trim()) {
        errors.username = "Email is required";
      }
      if (!credentials.apiToken?.trim()) {
        errors.apiToken = "API token is required";
      }
      if (!credentials.projectKey?.trim()) {
        errors.projectKey = "Project key is required";
      }
      break;

    case "servicenow":
      if (!credentials.instance?.trim()) {
        errors.instance = "Instance name is required";
      }
      if (!credentials.username?.trim()) {
        errors.username = "Username is required";
      }
      if (!credentials.password?.trim()) {
        errors.password = "Password is required";
      }
      break;

    case "github":
      if (!credentials.apiToken?.trim()) {
        errors.apiToken = "Personal access token is required";
      }
      if (!credentials.repository?.trim()) {
        errors.repository = "Repository is required (e.g., owner/repo)";
      }
      break;

    case "gitlab":
      if (!credentials.baseUrl?.trim()) {
        errors.baseUrl = "GitLab URL is required";
      } else if (!credentials.baseUrl.startsWith("https://")) {
        errors.baseUrl = "URL must start with https://";
      }
      if (!credentials.apiToken?.trim()) {
        errors.apiToken = "Personal access token is required";
      }
      break;
  }

  return errors;
}

/**
 * ConfigurationStep - Authentication configuration step
 *
 * Displays appropriate form fields based on the selected source tool.
 * Allows users to test their connection before proceeding.
 */
export function ConfigurationStep({
  config,
  onConfigUpdate,
}: ConfigurationStepProps): JSX.Element {
  const [connectionState, setConnectionState] =
    useState<ConnectionState>("idle");
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showToken, setShowToken] = useState(false);
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  const sourceTool = config.sourceTool;
  const credentials = config.credentials || {};

  /**
   * Update a credential field
   */
  const updateCredential = useCallback(
    (field: string, value: string) => {
      const updatedCredentials = {
        ...credentials,
        [field]: value,
      };
      onConfigUpdate({ credentials: updatedCredentials });

      // Clear error for this field
      if (formErrors[field]) {
        setFormErrors((prev) => {
          const next = { ...prev };
          delete next[field];
          return next;
        });
      }
    },
    [credentials, onConfigUpdate, formErrors]
  );

  /**
   * Test connection to the source tool
   */
  const handleTestConnection = useCallback(async () => {
    // Validate form first
    const errors = validateCredentials(sourceTool, credentials);
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    setConnectionState("testing");
    setConnectionError(null);

    try {
      // Call the backend API to test the connection
      const { INTEGRATION_API_URL } = await import("../../lib");
      const response = await fetch(
        `${INTEGRATION_API_URL}/api/imports/test-connection`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            source: sourceTool,
            source_config: credentials,
          }),
        }
      );

      const data = await response.json();

      if (response.ok && data.success) {
        setConnectionState("success");
      } else {
        const message = data.message || "Connection test failed";
        setConnectionError(message);
        setConnectionState("error");
      }
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to connect. Please check your credentials.";
      setConnectionError(message);
      setConnectionState("error");
    }
  }, [sourceTool, credentials]);

  /**
   * Render JIRA configuration form
   */
  const renderJiraForm = () => (
    <div className="space-y-4">
      {/* Base URL */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          JIRA URL <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <LinkIcon className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="url"
            value={credentials.baseUrl || ""}
            onChange={(e) => updateCredential("baseUrl", e.target.value)}
            placeholder="https://your-domain.atlassian.net"
            className={`
              block w-full pl-10 pr-3 py-2 border rounded-lg
              focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors
              ${formErrors.baseUrl ? "border-red-300" : "border-gray-300"}
            `}
          />
        </div>
        {formErrors.baseUrl && (
          <p className="mt-1 text-sm text-red-600">{formErrors.baseUrl}</p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          Your JIRA instance URL (e.g., https://company.atlassian.net)
        </p>
      </div>

      {/* Email */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Email Address <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <User className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="email"
            value={credentials.username || ""}
            onChange={(e) => updateCredential("username", e.target.value)}
            placeholder="your.email@company.com"
            className={`
              block w-full pl-10 pr-3 py-2 border rounded-lg
              focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors
              ${formErrors.username ? "border-red-300" : "border-gray-300"}
            `}
          />
        </div>
        {formErrors.username && (
          <p className="mt-1 text-sm text-red-600">{formErrors.username}</p>
        )}
      </div>

      {/* API Token */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          API Token <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Key className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type={showToken ? "text" : "password"}
            value={credentials.apiToken || ""}
            onChange={(e) => updateCredential("apiToken", e.target.value)}
            placeholder="Enter your JIRA API token"
            className={`
              block w-full pl-10 pr-10 py-2 border rounded-lg
              focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors
              ${formErrors.apiToken ? "border-red-300" : "border-gray-300"}
            `}
          />
          <button
            type="button"
            onClick={() => setShowToken(!showToken)}
            className="absolute inset-y-0 right-0 pr-3 flex items-center"
            aria-label={showToken ? "Hide token" : "Show token"}
          >
            {showToken ? (
              <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
            ) : (
              <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
            )}
          </button>
        </div>
        {formErrors.apiToken && (
          <p className="mt-1 text-sm text-red-600">{formErrors.apiToken}</p>
        )}
        <p className="mt-1 text-xs text-gray-500 flex items-start gap-1">
          <HelpCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
          <span>
            Create a token at: Account Settings → Security → API Tokens
          </span>
        </p>
      </div>

      {/* Project Key */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Project Key <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={credentials.projectKey || ""}
          onChange={(e) => updateCredential("projectKey", e.target.value)}
          placeholder="PROJ"
          className={`
            block w-full px-3 py-2 border rounded-lg
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors
            ${formErrors.projectKey ? "border-red-300" : "border-gray-300"}
          `}
        />
        {formErrors.projectKey && (
          <p className="mt-1 text-sm text-red-600">{formErrors.projectKey}</p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          The project key to import issues from (e.g., ACGS, DEV)
        </p>
      </div>
    </div>
  );

  /**
   * Render ServiceNow configuration form
   */
  const renderServiceNowForm = () => (
    <div className="space-y-4">
      {/* Instance */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Instance Name <span className="text-red-500">*</span>
        </label>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={credentials.instance || ""}
            onChange={(e) => updateCredential("instance", e.target.value)}
            placeholder="your-instance"
            className={`
              block w-full px-3 py-2 border rounded-lg
              focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors
              ${formErrors.instance ? "border-red-300" : "border-gray-300"}
            `}
          />
          <span className="text-gray-500 whitespace-nowrap">
            .service-now.com
          </span>
        </div>
        {formErrors.instance && (
          <p className="mt-1 text-sm text-red-600">{formErrors.instance}</p>
        )}
      </div>

      {/* Username */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Username <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <User className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            value={credentials.username || ""}
            onChange={(e) => updateCredential("username", e.target.value)}
            placeholder="Enter your ServiceNow username"
            className={`
              block w-full pl-10 pr-3 py-2 border rounded-lg
              focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors
              ${formErrors.username ? "border-red-300" : "border-gray-300"}
            `}
          />
        </div>
        {formErrors.username && (
          <p className="mt-1 text-sm text-red-600">{formErrors.username}</p>
        )}
      </div>

      {/* Password */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Password <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Key className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type={showPassword ? "text" : "password"}
            value={credentials.password || ""}
            onChange={(e) => updateCredential("password", e.target.value)}
            placeholder="Enter your ServiceNow password"
            className={`
              block w-full pl-10 pr-10 py-2 border rounded-lg
              focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors
              ${formErrors.password ? "border-red-300" : "border-gray-300"}
            `}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 pr-3 flex items-center"
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? (
              <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
            ) : (
              <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
            )}
          </button>
        </div>
        {formErrors.password && (
          <p className="mt-1 text-sm text-red-600">{formErrors.password}</p>
        )}
      </div>
    </div>
  );

  /**
   * Render GitHub configuration form
   */
  const renderGitHubForm = () => (
    <div className="space-y-4">
      {/* Personal Access Token */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Personal Access Token <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Key className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type={showToken ? "text" : "password"}
            value={credentials.apiToken || ""}
            onChange={(e) => updateCredential("apiToken", e.target.value)}
            placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
            className={`
              block w-full pl-10 pr-10 py-2 border rounded-lg
              focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors
              ${formErrors.apiToken ? "border-red-300" : "border-gray-300"}
            `}
          />
          <button
            type="button"
            onClick={() => setShowToken(!showToken)}
            className="absolute inset-y-0 right-0 pr-3 flex items-center"
            aria-label={showToken ? "Hide token" : "Show token"}
          >
            {showToken ? (
              <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
            ) : (
              <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
            )}
          </button>
        </div>
        {formErrors.apiToken && (
          <p className="mt-1 text-sm text-red-600">{formErrors.apiToken}</p>
        )}
        <p className="mt-1 text-xs text-gray-500 flex items-start gap-1">
          <HelpCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
          <span>
            Create a token at: Settings → Developer settings → Personal access
            tokens → Generate new token
          </span>
        </p>
      </div>

      {/* Repository */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Repository <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={credentials.repository || ""}
          onChange={(e) => updateCredential("repository", e.target.value)}
          placeholder="owner/repository"
          className={`
            block w-full px-3 py-2 border rounded-lg
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors
            ${formErrors.repository ? "border-red-300" : "border-gray-300"}
          `}
        />
        {formErrors.repository && (
          <p className="mt-1 text-sm text-red-600">{formErrors.repository}</p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          Format: owner/repository (e.g., facebook/react)
        </p>
      </div>
    </div>
  );

  /**
   * Render GitLab configuration form
   */
  const renderGitLabForm = () => (
    <div className="space-y-4">
      {/* Base URL */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          GitLab URL <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <LinkIcon className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="url"
            value={credentials.baseUrl || "https://gitlab.com"}
            onChange={(e) => updateCredential("baseUrl", e.target.value)}
            placeholder="https://gitlab.com"
            className={`
              block w-full pl-10 pr-3 py-2 border rounded-lg
              focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors
              ${formErrors.baseUrl ? "border-red-300" : "border-gray-300"}
            `}
          />
        </div>
        {formErrors.baseUrl && (
          <p className="mt-1 text-sm text-red-600">{formErrors.baseUrl}</p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          Use https://gitlab.com for GitLab.com or your self-hosted instance URL
        </p>
      </div>

      {/* Personal Access Token */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Personal Access Token <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Key className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type={showToken ? "text" : "password"}
            value={credentials.apiToken || ""}
            onChange={(e) => updateCredential("apiToken", e.target.value)}
            placeholder="glpat-xxxxxxxxxxxxxxxxxxxx"
            className={`
              block w-full pl-10 pr-10 py-2 border rounded-lg
              focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors
              ${formErrors.apiToken ? "border-red-300" : "border-gray-300"}
            `}
          />
          <button
            type="button"
            onClick={() => setShowToken(!showToken)}
            className="absolute inset-y-0 right-0 pr-3 flex items-center"
            aria-label={showToken ? "Hide token" : "Show token"}
          >
            {showToken ? (
              <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
            ) : (
              <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
            )}
          </button>
        </div>
        {formErrors.apiToken && (
          <p className="mt-1 text-sm text-red-600">{formErrors.apiToken}</p>
        )}
        <p className="mt-1 text-xs text-gray-500 flex items-start gap-1">
          <HelpCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
          <span>
            Create a token at: User Settings → Access Tokens → Add new token
            (requires 'api' scope)
          </span>
        </p>
      </div>

      {/* Project (optional) */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Project Path (optional)
        </label>
        <input
          type="text"
          value={credentials.projectKey || ""}
          onChange={(e) => updateCredential("projectKey", e.target.value)}
          placeholder="group/project or project-id"
          className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
        />
        <p className="mt-1 text-xs text-gray-500">
          Leave empty to import from all accessible projects
        </p>
      </div>
    </div>
  );

  /**
   * Render form based on selected source tool
   */
  const renderForm = () => {
    switch (sourceTool) {
      case "jira":
        return renderJiraForm();
      case "servicenow":
        return renderServiceNowForm();
      case "github":
        return renderGitHubForm();
      case "gitlab":
        return renderGitLabForm();
      default:
        return (
          <div className="text-center py-8 text-gray-500">
            Please select a source tool first
          </div>
        );
    }
  };

  if (!sourceTool) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="text-center py-12">
          <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No Source Selected
          </h3>
          <p className="text-gray-600">
            Please go back and select a data source first.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Configure {getSourceToolName(sourceTool)} Connection
        </h2>
        <p className="text-gray-600">
          Enter your authentication credentials to connect to{" "}
          {getSourceToolName(sourceTool)}. Your credentials are encrypted and
          stored securely.
        </p>
      </div>

      {/* Form */}
      <div className="bg-gray-50 rounded-lg p-6 mb-6">{renderForm()}</div>

      {/* Test Connection Button */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleTestConnection}
          disabled={connectionState === "testing"}
          className={`
            flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors
            ${
              connectionState === "testing"
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }
          `}
        >
          {connectionState === "testing" ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Testing Connection...
            </>
          ) : (
            <>
              <Key className="w-5 h-5" />
              Test Connection
            </>
          )}
        </button>

        {/* Connection Status */}
        {connectionState === "success" && (
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle2 className="w-5 h-5" />
            <span className="font-medium">Connection successful!</span>
          </div>
        )}
        {connectionState === "error" && connectionError && (
          <div className="flex items-center gap-2 text-red-600">
            <AlertCircle className="w-5 h-5" />
            <span className="font-medium">{connectionError}</span>
          </div>
        )}
      </div>

      {/* Success Message */}
      {connectionState === "success" && (
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-900">
            <strong className="font-semibold">Ready to proceed!</strong> Your
            credentials have been verified. Click "Next" to preview the data
            that will be imported.
          </p>
        </div>
      )}

      {/* Security Notice */}
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex gap-3">
          <HelpCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900">
            <p className="font-semibold mb-1">Security & Privacy</p>
            <p>
              Your credentials are encrypted using industry-standard encryption
              before being stored. We never log or expose your passwords or API
              tokens in plain text.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
