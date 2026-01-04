/**
 * ACGS-2 Template Upload Component
 * Constitutional Hash: 018-policy-marketplace
 *
 * Upload form for creating new policy templates with file validation.
 * Optimized with React.memo and useMemo for performance.
 */

import { memo, useState, useCallback, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { marketplaceAPI, ApiError } from "@services/api";
import type { TemplateCategory, TemplateResponse } from "@types/template";

// ====================
// Static Constants
// ====================

const ALLOWED_EXTENSIONS = [".json", ".yaml", ".yml", ".rego"] as const;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const categoryOptions: { value: TemplateCategory; label: string }[] = [
  { value: "compliance", label: "Compliance" },
  { value: "access_control", label: "Access Control" },
  { value: "data_protection", label: "Data Protection" },
  { value: "audit", label: "Audit" },
  { value: "rate_limiting", label: "Rate Limiting" },
  { value: "multi_tenant", label: "Multi-Tenant" },
  { value: "api_security", label: "API Security" },
  { value: "data_retention", label: "Data Retention" },
  { value: "custom", label: "Custom" },
] as const;

// ====================
// Helper Functions
// ====================

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
};

const getFileExtension = (filename: string): string => {
  const lastDot = filename.lastIndexOf(".");
  return lastDot !== -1 ? filename.slice(lastDot).toLowerCase() : "";
};

const isValidFileExtension = (filename: string): boolean => {
  const ext = getFileExtension(filename);
  return ALLOWED_EXTENSIONS.includes(ext as typeof ALLOWED_EXTENSIONS[number]);
};

// ====================
// Form State Interface
// ====================

interface FormState {
  name: string;
  description: string;
  category: TemplateCategory | "";
  file: File | null;
}

interface FormErrors {
  name?: string;
  description?: string;
  category?: string;
  file?: string;
}

// ====================
// Props Interface
// ====================

interface TemplateUploadProps {
  /** Callback when upload is successful */
  onSuccess?: (template: TemplateResponse) => void;
}

// ====================
// File Drop Zone Component
// ====================

interface FileDropZoneProps {
  file: File | null;
  error?: string;
  onFileSelect: (file: File) => void;
  onFileClear: () => void;
}

const FileDropZone = memo(function FileDropZone({
  file,
  error,
  onFileSelect,
  onFileClear,
}: FileDropZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) {
        onFileSelect(droppedFile);
      }
    },
    [onFileSelect]
  );

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0];
      if (selectedFile) {
        onFileSelect(selectedFile);
      }
    },
    [onFileSelect]
  );

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleClear = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onFileClear();
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [onFileClear]
  );

  const acceptTypes = useMemo(
    () => ALLOWED_EXTENSIONS.join(","),
    []
  );

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        Template File <span className="text-red-500">*</span>
      </label>
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-lg p-6 cursor-pointer
          transition-colors duration-200
          ${
            isDragging
              ? "border-blue-500 bg-blue-50"
              : error
              ? "border-red-300 bg-red-50"
              : file
              ? "border-green-300 bg-green-50"
              : "border-gray-300 hover:border-gray-400"
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptTypes}
          onChange={handleFileInputChange}
          className="hidden"
        />

        {file ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <svg
                className="w-10 h-10 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <div>
                <p className="text-sm font-medium text-gray-900">{file.name}</p>
                <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleClear}
              className="
                p-2 text-gray-400 hover:text-red-500
                transition-colors rounded-full hover:bg-red-100
              "
              title="Remove file"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        ) : (
          <div className="text-center">
            <svg
              className="w-12 h-12 mx-auto text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="mt-2 text-sm text-gray-600">
              <span className="font-medium text-blue-600">Click to upload</span> or drag and drop
            </p>
            <p className="mt-1 text-xs text-gray-500">
              {ALLOWED_EXTENSIONS.join(", ")} (max {formatFileSize(MAX_FILE_SIZE)})
            </p>
          </div>
        )}
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
});

// ====================
// Text Input Component
// ====================

interface TextInputProps {
  id: string;
  label: string;
  value: string;
  error?: string;
  required?: boolean;
  placeholder?: string;
  onChange: (value: string) => void;
}

const TextInput = memo(function TextInput({
  id,
  label,
  value,
  error,
  required,
  placeholder,
  onChange,
}: TextInputProps) {
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(e.target.value);
    },
    [onChange]
  );

  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block text-sm font-medium text-gray-700">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        id={id}
        type="text"
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        className={`
          w-full px-4 py-2 border rounded-md
          focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          transition-colors
          ${error ? "border-red-300 bg-red-50" : "border-gray-300"}
        `}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
});

// ====================
// Text Area Component
// ====================

interface TextAreaProps {
  id: string;
  label: string;
  value: string;
  error?: string;
  required?: boolean;
  placeholder?: string;
  rows?: number;
  onChange: (value: string) => void;
}

const TextArea = memo(function TextArea({
  id,
  label,
  value,
  error,
  required,
  placeholder,
  rows = 4,
  onChange,
}: TextAreaProps) {
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange(e.target.value);
    },
    [onChange]
  );

  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block text-sm font-medium text-gray-700">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <textarea
        id={id}
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        rows={rows}
        className={`
          w-full px-4 py-2 border rounded-md
          focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          transition-colors resize-y
          ${error ? "border-red-300 bg-red-50" : "border-gray-300"}
        `}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
});

// ====================
// Select Component
// ====================

interface SelectProps {
  id: string;
  label: string;
  value: string;
  error?: string;
  required?: boolean;
  options: readonly { value: string; label: string }[];
  placeholder?: string;
  onChange: (value: string) => void;
}

const Select = memo(function Select({
  id,
  label,
  value,
  error,
  required,
  options,
  placeholder,
  onChange,
}: SelectProps) {
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      onChange(e.target.value);
    },
    [onChange]
  );

  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block text-sm font-medium text-gray-700">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <select
        id={id}
        value={value}
        onChange={handleChange}
        className={`
          w-full px-4 py-2 border rounded-md
          focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          transition-colors
          ${error ? "border-red-300 bg-red-50" : "border-gray-300"}
        `}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
});

// ====================
// Success Message Component
// ====================

interface SuccessMessageProps {
  template: TemplateResponse;
  onViewTemplate: () => void;
  onUploadAnother: () => void;
}

const SuccessMessage = memo(function SuccessMessage({
  template,
  onViewTemplate,
  onUploadAnother,
}: SuccessMessageProps) {
  return (
    <div className="text-center py-8">
      <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
        <svg
          className="w-8 h-8 text-green-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
          />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        Template Uploaded Successfully!
      </h3>
      <p className="text-sm text-gray-600 mb-6">
        Your template &ldquo;{template.name}&rdquo; has been uploaded and is ready for review.
      </p>
      <div className="flex justify-center gap-4">
        <button
          onClick={onViewTemplate}
          className="
            px-4 py-2 bg-blue-600 text-white rounded-md
            hover:bg-blue-700 transition-colors
          "
        >
          View Template
        </button>
        <button
          onClick={onUploadAnother}
          className="
            px-4 py-2 border border-gray-300 text-gray-700 rounded-md
            hover:bg-gray-50 transition-colors
          "
        >
          Upload Another
        </button>
      </div>
    </div>
  );
});

// ====================
// Main Component
// ====================

function TemplateUploadComponent({
  onSuccess,
}: TemplateUploadProps): JSX.Element {
  const navigate = useNavigate();

  // Form state
  const [formState, setFormState] = useState<FormState>({
    name: "",
    description: "",
    category: "",
    file: null,
  });

  // UI state
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [uploadedTemplate, setUploadedTemplate] = useState<TemplateResponse | null>(null);

  // Validation
  const validateForm = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    // Name validation
    if (!formState.name.trim()) {
      newErrors.name = "Template name is required";
    } else if (formState.name.trim().length < 3) {
      newErrors.name = "Template name must be at least 3 characters";
    } else if (formState.name.trim().length > 255) {
      newErrors.name = "Template name must be less than 255 characters";
    }

    // Description validation
    if (!formState.description.trim()) {
      newErrors.description = "Description is required";
    } else if (formState.description.trim().length < 10) {
      newErrors.description = "Description must be at least 10 characters";
    }

    // Category validation
    if (!formState.category) {
      newErrors.category = "Please select a category";
    }

    // File validation
    if (!formState.file) {
      newErrors.file = "Please select a template file";
    } else {
      if (!isValidFileExtension(formState.file.name)) {
        newErrors.file = `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
      } else if (formState.file.size > MAX_FILE_SIZE) {
        newErrors.file = `File size exceeds ${formatFileSize(MAX_FILE_SIZE)}`;
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formState]);

  // Form field handlers
  const handleNameChange = useCallback((value: string) => {
    setFormState((prev) => ({ ...prev, name: value }));
    setErrors((prev) => ({ ...prev, name: undefined }));
  }, []);

  const handleDescriptionChange = useCallback((value: string) => {
    setFormState((prev) => ({ ...prev, description: value }));
    setErrors((prev) => ({ ...prev, description: undefined }));
  }, []);

  const handleCategoryChange = useCallback((value: string) => {
    setFormState((prev) => ({ ...prev, category: value as TemplateCategory }));
    setErrors((prev) => ({ ...prev, category: undefined }));
  }, []);

  const handleFileSelect = useCallback((file: File) => {
    // Validate file before setting
    let fileError: string | undefined;
    if (!isValidFileExtension(file.name)) {
      fileError = `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
    } else if (file.size > MAX_FILE_SIZE) {
      fileError = `File size exceeds ${formatFileSize(MAX_FILE_SIZE)}`;
    }

    setFormState((prev) => ({ ...prev, file }));
    setErrors((prev) => ({ ...prev, file: fileError }));
  }, []);

  const handleFileClear = useCallback(() => {
    setFormState((prev) => ({ ...prev, file: null }));
    setErrors((prev) => ({ ...prev, file: undefined }));
  }, []);

  // Form submission
  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setSubmitError(null);

      if (!validateForm()) {
        return;
      }

      setIsSubmitting(true);

      try {
        const template = await marketplaceAPI.uploadTemplate(
          formState.file!,
          formState.name.trim(),
          formState.description.trim(),
          formState.category as TemplateCategory
        );

        setUploadedTemplate(template);
        onSuccess?.(template);
      } catch (err) {
        if (err instanceof ApiError) {
          setSubmitError(err.detail || err.message);
        } else if (err instanceof Error) {
          setSubmitError(err.message);
        } else {
          setSubmitError("An unexpected error occurred. Please try again.");
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [formState, validateForm, onSuccess]
  );

  // Success state handlers
  const handleViewTemplate = useCallback(() => {
    if (uploadedTemplate) {
      navigate(`/templates/${uploadedTemplate.id}`);
    }
  }, [navigate, uploadedTemplate]);

  const handleUploadAnother = useCallback(() => {
    setFormState({
      name: "",
      description: "",
      category: "",
      file: null,
    });
    setErrors({});
    setSubmitError(null);
    setUploadedTemplate(null);
  }, []);

  // Check if form is valid for submit button
  const isFormValid = useMemo(() => {
    return (
      formState.name.trim().length >= 3 &&
      formState.description.trim().length >= 10 &&
      formState.category !== "" &&
      formState.file !== null &&
      isValidFileExtension(formState.file.name) &&
      formState.file.size <= MAX_FILE_SIZE
    );
  }, [formState]);

  // Render success state
  if (uploadedTemplate) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <SuccessMessage
          template={uploadedTemplate}
          onViewTemplate={handleViewTemplate}
          onUploadAnother={handleUploadAnother}
        />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">Upload Template</h2>
        <p className="text-sm text-gray-500 mt-1">
          Share your governance policy template with the community
        </p>
      </div>

      {/* Submit Error */}
      {submitError && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-center gap-2">
            <svg
              className="w-5 h-5 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <p className="text-sm text-red-600">{submitError}</p>
          </div>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* File Upload */}
        <FileDropZone
          file={formState.file}
          error={errors.file}
          onFileSelect={handleFileSelect}
          onFileClear={handleFileClear}
        />

        {/* Template Name */}
        <TextInput
          id="template-name"
          label="Template Name"
          value={formState.name}
          error={errors.name}
          required
          placeholder="e.g., GDPR Compliance Policy"
          onChange={handleNameChange}
        />

        {/* Description */}
        <TextArea
          id="template-description"
          label="Description"
          value={formState.description}
          error={errors.description}
          required
          placeholder="Describe what this template does and when to use it..."
          rows={4}
          onChange={handleDescriptionChange}
        />

        {/* Category */}
        <Select
          id="template-category"
          label="Category"
          value={formState.category}
          error={errors.category}
          required
          options={categoryOptions}
          placeholder="Select a category..."
          onChange={handleCategoryChange}
        />

        {/* Info Box */}
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
          <div className="flex items-start gap-3">
            <svg
              className="w-5 h-5 text-blue-600 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div className="text-sm text-blue-700">
              <p className="font-medium mb-1">Template Guidelines</p>
              <ul className="list-disc list-inside space-y-1 text-blue-600">
                <li>Templates will be reviewed before being published</li>
                <li>Ensure your template follows ACGS-2 governance standards</li>
                <li>Include clear documentation within the template</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex items-center justify-end gap-4 pt-4 border-t border-gray-200">
          <button
            type="button"
            onClick={() => navigate("/templates")}
            className="
              px-4 py-2 border border-gray-300 text-gray-700 rounded-md
              hover:bg-gray-50 transition-colors
            "
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!isFormValid || isSubmitting}
            className="
              px-6 py-2 bg-blue-600 text-white rounded-md
              hover:bg-blue-700 transition-colors
              disabled:opacity-50 disabled:cursor-not-allowed
              flex items-center gap-2
            "
          >
            {isSubmitting ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Uploading...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
                Upload Template
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

// Memoize to prevent re-renders when parent updates with same props
export const TemplateUpload = memo(TemplateUploadComponent);
