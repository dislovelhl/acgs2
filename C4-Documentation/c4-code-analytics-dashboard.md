# C4 Code Level: Analytics Dashboard Frontend

## Overview

- **Name**: ACGS-2 Analytics Dashboard Frontend
- **Description**: React/TypeScript web-based dashboard for AI governance analytics, compliance monitoring, and real-time performance insights. Provides interactive widgets for anomaly detection, compliance status, violation forecasting, and AI-generated insights with drag-and-drop layout customization.
- **Location**: `/home/dislove/document/acgs2/src/frontend/analytics-dashboard`
- **Language**: TypeScript (React 18+)
- **Purpose**: Web frontend for visualizing, querying, and analyzing governance analytics with natural language interfaces and responsive dashboard layouts. Serves as the primary user interface for compliance officers, AI engineers, and governance teams.

## Code Elements

### Core Application Entry Points

#### `App()` (Function Component)
- **Location**: `/src/App.tsx:46-55`
- **Description**: Root application component implementing React Router for multi-page navigation with two main routes: dashboard view and data import page
- **Signature**: `function App(): JSX.Element`
- **Returns**: JSX.Element (BrowserRouter with Routes)
- **Dependencies**:
  - `react-router-dom`: BrowserRouter, Routes, Route
  - `./layouts/DashboardGrid`: DashboardGrid component
  - `./components/QueryInterface`: QueryInterface component
  - `./pages/ImportDataPage`: ImportDataPage component

#### `DashboardPage()` (Function Component)
- **Location**: `/src/App.tsx:17-41`
- **Description**: Main dashboard view component displaying page header, query interface, and customizable widget grid
- **Signature**: `function DashboardPage(): JSX.Element`
- **Returns**: JSX.Element (HTML structure with header and main content area)
- **Dependencies**:
  - `./layouts/DashboardGrid`: Main dashboard grid layout
  - `./components/QueryInterface`: Natural language query input

#### `main.tsx` (Entry Point)
- **Location**: `/src/main.tsx:1-19`
- **Description**: React application initialization and rendering to DOM. Loads required CSS files for react-grid-layout and react-resizable
- **Key Functions**:
  - `ReactDOM.createRoot()`: Creates React 18 root
  - CSS imports for grid layout styling

### Layout Components

#### `DashboardGrid()` (Function Component)
- **Location**: `/src/layouts/DashboardGrid.tsx:236-509`
- **Signature**: `function DashboardGrid(): JSX.Element`
- **Description**: Main dashboard layout component implementing react-grid-layout with responsive breakpoints, drag-and-drop widget repositioning, and localStorage persistence
- **Returns**: JSX.Element (Responsive grid layout with draggable widgets)
- **Key State**:
  - `layouts: Layouts` - Current layout configuration for all breakpoints
  - `isLocked: boolean` - Controls whether widgets can be moved/resized
  - `mounted: boolean` - Hydration safety flag
- **Key Methods**:
  - `handleLayoutChange(currentLayout: Layout[], allLayouts: Layouts): void` (line 254-260) - Updates and persists layout changes
  - `handleResetLayout(): void` (line 265-269) - Resets layouts to defaults
  - `handleToggleLock(): void` (line 274-276) - Toggles layout lock state
- **Responsive Breakpoints** (line 79-83):
  - lg: 1200px (12 columns), md: 996px (10 columns), sm: 768px (6 columns), xs: 480px (4 columns), xxs: 0px (2 columns)
- **Widget Configurations** (line 52-77): InsightWidget, AnomalyWidget, PredictionWidget, ComplianceWidget
- **Dependencies**:
  - `react-grid-layout`: Responsive, WidthProvider, Layout, Layouts types
  - `lucide-react`: Icons (GripVertical, Lock, RotateCcw, Unlock)
  - Widget components and Tooltip

#### `generateDefaultLayouts()` (Function)
- **Location**: `/src/layouts/DashboardGrid.tsx:91-145`
- **Signature**: `function generateDefaultLayouts(): Layouts`
- **Description**: Generates default layout configurations for all responsive breakpoints with widget positions and sizes
- **Returns**: Layouts object with breakpoint-specific arrays of Layout items
- **Dependencies**: WIDGET_CONFIGS, BREAKPOINTS constants

#### `saveLayoutsToStorage(layouts: Layouts): void` (Function)
- **Location**: `/src/layouts/DashboardGrid.tsx:150-159`
- **Description**: Persists layouts to browser localStorage with error handling
- **Parameters**: layouts (Layouts) - Layout configuration to save
- **Handles**: localStorage quota exceeded errors gracefully

#### `loadLayoutsFromStorage(): Layouts | null` (Function)
- **Location**: `/src/layouts/DashboardGrid.tsx:164-223`
- **Signature**: `function loadLayoutsFromStorage(): Layouts | null`
- **Description**: Loads and validates layouts from localStorage, returning null on parse errors or invalid data
- **Returns**: Layouts object or null if not found/invalid
- **Validation**: Checks for valid breakpoints, array structures, and required properties (i, x, y, w, h)

### Widget Components

#### `InsightWidget()` (Memoized Function Component)
- **Location**: `/src/components/widgets/InsightWidget.tsx:86-305`
- **Signature**: `export const InsightWidget = memo(function InsightWidget(): JSX.Element)`
- **Description**: Displays AI-generated governance insights with summary, business impact analysis, and recommended actions. Memoized to prevent unnecessary re-renders
- **Returns**: JSX.Element (Widget card with insight data or loading/error states)
- **Key State**:
  - `insight: InsightData | null` - Fetched insight data
  - `loadingState: LoadingState` - Loading state (idle, loading, success, error)
  - `error: string | null` - Error message if fetch fails
- **Key Methods**:
  - `fetchInsight(forceRefresh?: boolean): Promise<void>` (line 106-139) - Fetches insight data from API
  - `handleRefresh(): void` (line 149-151) - Triggers refresh with cache bypass
- **Data Structure** (InsightData):
  - summary, business_impact, recommended_action (strings)
  - confidence (0-1 float), generated_at (ISO string), model_used, cached (boolean)
- **API Endpoint**: GET `/insights` with optional `refresh=true` query parameter
- **Dependencies**: lucide-react icons, API_BASE_URL config

#### `AnomalyWidget()` (Function Component)
- **Location**: `/src/components/widgets/AnomalyWidget.tsx:125-399`
- **Signature**: `function AnomalyWidget(): JSX.Element`
- **Description**: Displays detected anomalies in governance metrics with severity filtering and affected metrics breakdown
- **Returns**: JSX.Element (Widget card with anomaly list or loading/error states)
- **Key State**:
  - `severityFilter: string | null` - Current severity filter (critical, high, medium, low, or null for all)
  - Data/loading/error from `useAnomalies()` hook
- **Key Methods**:
  - `handleRefresh(): void` (line 132-134) - Calls hook's refetch function
  - `handleFilterChange(severity: string | null): void` (line 139-141) - Updates severity filter
- **Helper Functions**:
  - `getSeverityIcon(severity): JSX.Element` (line 25-38) - Returns icon for severity level
  - `getSeverityColors(severity): ColorClasses` (line 43-86) - Returns Tailwind color classes
  - `formatTimestamp(timestamp: string): string` (line 91-101) - Formats ISO timestamps
  - `formatAffectedMetrics(metrics: Record): string[]` (line 106-113) - Formats metrics for display
- **Dependencies**:
  - `useAnomalies()` hook from `/hooks/useAnomalies.ts`
  - lucide-react icons
  - AnomalyItem type from `/types/anomalies.ts`

#### `ComplianceWidget()` (Function Component)
- **Location**: `/src/components/widgets/ComplianceWidget.tsx:186-544`
- **Signature**: `function ComplianceWidget(): JSX.Element`
- **Description**: Displays real-time compliance status including overall compliance rate, trend direction, violations by severity, and recent violations list
- **Returns**: JSX.Element (Widget card with compliance data or loading/error states)
- **Key State**:
  - `data: ComplianceData | null` - Compliance data from API
  - `loadingState: LoadingState` - Loading state
  - `error: string | null` - Error message
  - `severityFilter: Severity | null` - Current severity filter
- **Key Methods**:
  - `fetchCompliance(): Promise<void>` (line 195-229) - Fetches compliance data with optional severity filter
  - `handleRefresh(): void` (line 239-241) - Triggers data refresh
  - `handleFilterChange(severity: Severity | null): void` (line 246-248) - Updates severity filter
- **Data Structure** (ComplianceData):
  - overall_score (0-100 float)
  - trend (improving/stable/declining)
  - violations_by_severity (object with critical, high, medium, low counts)
  - recent_violations (array of ComplianceViolation)
  - frameworks_analyzed (string array)
- **Helper Functions**:
  - `getSeverityIcon(severity: Severity): JSX.Element` (line 64-77)
  - `getSeverityColors(severity: Severity): ColorClasses` (line 82-125)
  - `getTrendIcon(trend: ComplianceTrend): JSX.Element` (line 130-141)
  - `getTrendColor(trend: ComplianceTrend): string` (line 146-157)
  - `formatTimestamp(timestamp: string): string` (line 162-172)
- **API Endpoint**: GET `/compliance` with optional `severity` query parameter
- **Dependencies**: lucide-react icons, API_BASE_URL config

#### `PredictionWidget()` (Memoized Function Component)
- **Location**: `/src/components/widgets/PredictionWidget.tsx:1-100+`
- **Description**: Displays 30-day violation forecast with confidence intervals, trend analysis, and summary statistics using Recharts for visualization
- **Data Structure** (PredictionsResponse):
  - predictions (array of PredictionPoint with date, predicted_value, bounds)
  - summary (PredictionSummary with mean, max, min, trend_direction)
  - model_trained (boolean)
- **Key Methods**:
  - `fetchPredictions(forceRefresh?: boolean): Promise<void>` - Fetches prediction data
  - `getTrendIcon(direction: string | null): JSX.Element` (line 75-86)
  - `getTrendColor(direction: string | null): string` (line 91-100)
- **Chart Components**: Uses Recharts ComposedChart, Area, Line, Tooltip, XAxis, YAxis
- **Dependencies**: Recharts, lucide-react icons

### Query and Search Components

#### `QueryInterface()` (Function Component)
- **Location**: `/src/components/QueryInterface.tsx:88-431`
- **Signature**: `function QueryInterface(): JSX.Element`
- **Description**: Natural language query interface for governance data with sample queries, query history, and response display
- **Returns**: JSX.Element (Query input form with results section)
- **Key State**:
  - `query: string` - Current query text
  - `loadingState: LoadingState` - Submission state
  - `error: string | null` - Error message
  - `currentResponse: QueryResponse | null` - Latest query response
  - `queryHistory: QueryHistoryItem[]` - Recent queries (max 5)
  - `showHistory: boolean` - History panel visibility
  - `showSamples: boolean` - Sample queries visibility
- **Key Methods**:
  - `submitQuery(queryText: string): Promise<void>` (line 112-158) - Submits query to API
  - `handleSubmit(e: React.FormEvent): void` (line 163-166) - Form submission handler
  - `handleSampleClick(sampleQuery: string): void` (line 171-174) - Clicks sample query
  - `handleHistoryClick(item: QueryHistoryItem): void` (line 179-184) - Loads history item
  - `handleClear(): void` (line 189-196) - Resets form and results
- **Helper Functions**:
  - `formatTimestamp(date: Date): string` (line 58-63) - Formats Date object
  - `formatDataValue(value: unknown): string` (line 68-76) - Formats data values for display
- **Data Structures**:
  - QueryResponse: { query, answer, data, query_understood, generated_at }
  - QueryHistoryItem: { query, response, timestamp }
- **Sample Queries** (line 47-53): Predefined example queries for users
- **API Endpoint**: POST `/query` with `{ question: string }`
- **Dependencies**: lucide-react icons, API_BASE_URL config, LoadingState type

#### `SkipLink()` (Function Component)
- **Location**: `/src/components/SkipLink.tsx`
- **Description**: Accessibility skip link component for keyboard navigation to main content
- **Returns**: JSX.Element (Skip to main content link)

### Common Components

#### `LoadingOverlay()` (Function Component)
- **Location**: `/src/components/LoadingOverlay.tsx:39-66`
- **Signature**: `function LoadingOverlay(props: LoadingOverlayProps): JSX.Element | null`
- **Description**: Semi-transparent overlay with centered spinner and optional loading message
- **Parameters**:
  - `show: boolean` - Controls visibility
  - `message?: string` - Optional loading message (default: "Loading...")
- **Returns**: JSX.Element | null (Overlay or null if not shown)
- **Positioning**: Absolute positioned to overlay parent container (parent must have position: relative)
- **Accessibility**: ARIA labels (role="status", aria-live="polite", aria-hidden on icon)
- **Dependencies**: lucide-react RefreshCw icon

#### `Tooltip()` (Function Component)
- **Location**: `/src/components/common/Tooltip.tsx`
- **Description**: Reusable tooltip component for contextual help
- **Parameters**: content (ReactNode), position (top/bottom/left/right), children
- **Returns**: JSX.Element (Wrapper with tooltip on hover)
- **Dependencies**: lucide-react icons, Tailwind CSS

### Import Components

#### `ImportWizard()` (Function Component)
- **Location**: `/src/components/ImportWizard/ImportWizard.tsx:100+`
- **Signature**: `function ImportWizard(props: ImportWizardProps): JSX.Element`
- **Description**: Multi-step wizard for importing data from external sources (JIRA, ServiceNow, GitHub, GitLab)
- **Props**:
  - `onComplete: () => void` - Callback on successful import
  - `onCancel: () => void` - Callback on user cancellation
- **Wizard Steps** (line 73-90):
  1. SourceSelectionStep - Select data source tool
  2. ConfigurationStep - Configure authentication
  3. PreviewStep - Preview data before import
  4. ProgressStep - Track import progress
- **State**:
  - `currentStep: number` - Current wizard step (0-3)
  - `config: ImportConfig` - Shared configuration across steps
- **Helper Components**:
  - `StepIndicator()` (line 94-150) - Visual progress indicator

#### `SourceSelectionStep()` (Function Component)
- **Location**: `/src/components/ImportWizard/SourceSelectionStep.tsx`
- **Description**: Step for selecting external data source tool
- **Supported Sources**: JIRA, ServiceNow, GitHub, GitLab

#### `ConfigurationStep()` (Function Component)
- **Location**: `/src/components/ImportWizard/ConfigurationStep.tsx`
- **Description**: Step for entering authentication credentials and tool-specific configuration
- **Modified**: (M) Mon Jan 4 05:30 - Configuration options updates

#### `PreviewStep()` (Function Component)
- **Location**: `/src/components/ImportWizard/PreviewStep.tsx`
- **Description**: Step for previewing sample data before executing import
- **Modified**: (M) Mon Jan 4 05:30 - Preview data formatting

#### `ProgressStep()` (Function Component)
- **Location**: `/src/components/ImportWizard/ProgressStep.tsx`
- **Description**: Step for tracking import job progress with real-time status updates
- **Modified**: (M) Mon Jan 4 05:30 - Progress tracking enhancements

#### `HelpPanel()` (Function Component)
- **Location**: `/src/components/ImportWizard/HelpPanel.tsx`
- **Description**: Contextual help panel for import wizard with step-specific guidance

#### `ImportDataPage()` (Function Component)
- **Location**: `/src/pages/ImportDataPage.tsx`
- **Description**: Page component wrapping the import wizard with routing

### Custom Hooks

#### `useAnomalies(severityFilter?: string | null)` (Hook)
- **Location**: `/src/hooks/useAnomalies.ts:96-143`
- **Signature**: `function useAnomalies(severityFilter?: string | null): UseDataResult<AnomaliesResponse>`
- **Description**: Custom data-fetching hook for anomaly detection data with optional severity filtering
- **Parameters**:
  - `severityFilter?: string | null` - Filter anomalies by severity (critical, high, medium, low)
- **Returns**: UseDataResult<AnomaliesResponse>
  - `data: AnomaliesResponse | null` - Anomaly response data
  - `loading: boolean` - Fetch in progress
  - `error: Error | null` - Fetch error
  - `refetch: () => Promise<void>` - Manual refresh function
- **Key Methods**:
  - `fetchAnomalies(): Promise<void>` (line 103-136) - Fetches from API with severity filter
- **API Endpoint**: GET `/anomalies?severity={filter}` (if filter provided)
- **Dependencies**: ANALYTICS_API_URL config, AnomaliesResponse type, UseDataResult type
- **Hook Pattern**: Follows standard React hooks conventions with useCallback and useEffect

### Type Definitions

#### `LoadingState` (Union Type)
- **Location**: `/src/lib/types.ts:30`
- **Definition**: `type LoadingState = "idle" | "loading" | "success" | "error"`
- **Usage**: Represents component loading states across all widgets and async operations
- **Values**:
  - "idle": Initial state, no operation started
  - "loading": Async operation in progress
  - "success": Operation completed successfully
  - "error": Operation failed

#### `UseDataResult<T>` (Generic Interface)
- **Location**: `/src/hooks/types.ts:12-21`
- **Definition**:
  ```typescript
  interface UseDataResult<T> {
    data: T | null;
    loading: boolean;
    error: Error | null;
    refetch: () => Promise<void>;
  }
  ```
- **Usage**: Standard return type for all data-fetching hooks
- **Type Parameters**: T - The type of fetched data

#### `AnomalyItem` (Interface)
- **Location**: `/src/types/anomalies.ts:14-32`
- **Properties**:
  - `anomaly_id: string` - Unique identifier
  - `timestamp: string` - ISO detection timestamp
  - `severity_score: number` - 0-1 score
  - `severity_label: "critical" | "high" | "medium" | "low"` - Severity classification
  - `affected_metrics: Record<string, number | string>` - Affected metrics
  - `description: string` - Anomaly description

#### `AnomaliesResponse` (Interface)
- **Location**: `/src/types/anomalies.ts:40-58`
- **Properties**:
  - `analysis_timestamp: string` - ISO analysis timestamp
  - `total_records_analyzed: number` - Records in analysis
  - `anomalies_detected: number` - Count of anomalies found
  - `contamination_rate: number` - Model contamination rate
  - `anomalies: AnomalyItem[]` - Array of detected anomalies
  - `model_trained: boolean` - Whether model is trained

#### `ImportConfig` (Interface)
- **Location**: `/src/components/ImportWizard/ImportWizard.tsx:26-52`
- **Properties**:
  - `sourceTool?: SourceTool` - Selected tool (jira, servicenow, github, gitlab)
  - `credentials?: { ... }` - Tool-specific authentication
  - `previewData?: { ... }` - Preview items and count
  - `jobId?: string` - Import job tracking ID

#### `ComplianceData` (Interface)
- **Location**: `/src/components/widgets/ComplianceWidget.tsx:51-59`
- **Properties**:
  - `overall_score: number` - Compliance percentage (0-100)
  - `trend: ComplianceTrend` - Trend direction
  - `violations_by_severity: ViolationsBySeverity` - Violation counts
  - `recent_violations: ComplianceViolation[]` - Recent violations list
  - `frameworks_analyzed: string[]` - Compliance frameworks

#### `InsightData` (Interface)
- **Location**: `/src/components/widgets/InsightWidget.tsx:22-30`
- **Properties**:
  - `summary: string` - Insight summary
  - `business_impact: string` - Business impact analysis
  - `recommended_action: string` - Recommended action
  - `confidence: number` - Confidence score (0-1)
  - `generated_at: string` - ISO timestamp
  - `model_used: string | null` - Model identifier
  - `cached: boolean` - Whether result is cached

#### `PredictionPoint` (Interface)
- **Location**: `/src/components/widgets/PredictionWidget.tsx:32-38`
- **Properties**:
  - `date: string` - Prediction date
  - `predicted_value: number` - Predicted violation count
  - `lower_bound: number` - Confidence interval lower bound
  - `upper_bound: number` - Confidence interval upper bound
  - `trend: number` - Trend coefficient

### Configuration and Services

#### `config.ts` (Module)
- **Location**: `/src/lib/config.ts:1-16`
- **Exports**:
  - `ANALYTICS_API_URL: string` - Analytics API base URL (env: VITE_ANALYTICS_API_URL)
  - `INTEGRATION_API_URL: string` - Integration API base URL (env: VITE_INTEGRATION_API_URL)
  - `API_BASE_URL: string` - (deprecated) Alias for ANALYTICS_API_URL

#### `importApi.ts` (Module)
- **Location**: `/src/services/importApi.ts:1-402`
- **Exported Functions**:
  - `previewImport(request: ImportRequest): Promise<PreviewResponse>` (line 202-234)
  - `executeImport(request: ImportRequest): Promise<ImportResponse>` (line 243-275)
  - `getImportStatus(jobId: string): Promise<ImportResponse>` (line 284-312)
  - `listImports(options?: {...}): Promise<ImportListResponse>` (line 321-364)
  - `cancelImport(jobId: string): Promise<ImportResponse>` (line 373-401)
- **Exported Types**:
  - `SourceType`, `ImportStatus`, `DuplicateHandling`, `SourceConfig`
  - `ImportOptions`, `ImportRequest`, `PreviewResponse`, `PreviewItem`
  - `ImportProgress`, `ImportedItem`, `ImportResponse`, `ImportListResponse`
  - `ImportApiError` (custom error class)
- **API Base URL**: VITE_INTEGRATION_API_URL or http://localhost:8100
- **Endpoints**:
  - POST `/api/imports/preview` - Preview import data
  - POST `/api/imports` - Execute import
  - GET `/api/imports/{jobId}` - Get import status
  - GET `/api/imports` - List imports
  - DELETE `/api/imports/{jobId}` - Cancel import

### Chart Components

#### `ResponsiveChart()` (Function Component)
- **Location**: `/src/components/charts/ResponsiveChart.tsx`
- **Description**: Wrapper for responsive chart rendering with Recharts

#### `AreaChart()` (Function Component)
- **Location**: `/src/components/charts/AreaChart.tsx`
- **Description**: Area chart component for time-series data visualization

#### `LineChart()` (Function Component)
- **Location**: `/src/components/charts/LineChart.tsx`
- **Description**: Line chart component for trend visualization

#### `ComposedChart()` (Function Component)
- **Location**: `/src/components/charts/ComposedChart.tsx`
- **Description**: Composed chart combining multiple chart types

### Testing Infrastructure

#### Test Files
- `/src/components/common/__tests__/Tooltip.test.tsx` - Tooltip component tests
- `/src/components/__tests__/QueryInterface.test.tsx` - QueryInterface tests
- `/src/components/widgets/__tests__/AnomalyWidget.test.tsx` - Anomaly widget tests
- `/src/components/widgets/__tests__/ComplianceWidget.test.tsx` - Compliance widget tests
- `/src/components/widgets/__tests__/InsightWidget.test.tsx` - Insight widget tests
- `/src/components/widgets/__tests__/PredictionWidget.test.tsx` - Prediction widget tests
- `/src/layouts/__tests__/DashboardGrid.test.tsx` - Dashboard grid layout tests
- `/src/test/hooks/useAnomalies.test.ts` - useAnomalies hook tests
- `/src/test/integration/dashboard_api_integration.test.tsx` - API integration tests
- `/src/test/e2e/verify_dashboard_integration.ts` - End-to-end verification

#### Mock Infrastructure
- `/src/test/mocks/handlers.ts` - MSW request handlers
- `/src/test/mocks/server.ts` - MSW server setup
- `/src/test/setupTests.ts` - Test environment setup

## Dependencies

### Internal Dependencies

#### Components (Interdependencies)
- `DashboardGrid` imports: InsightWidget, AnomalyWidget, PredictionWidget, ComplianceWidget, Tooltip
- `ImportWizard` imports: SourceSelectionStep, ConfigurationStep, PreviewStep, ProgressStep, HelpPanel
- All widgets import: LoadingOverlay, LoadingState type
- `AnomalyWidget` imports: useAnomalies hook, AnomalyItem type

#### Hooks
- `useAnomalies` imports: UseDataResult type, AnomaliesResponse type, ANALYTICS_API_URL
- All data-fetching components use: LoadingState type from `/lib/types.ts`

#### Configuration and Utilities
- All API-calling components import: API_BASE_URL or ANALYTICS_API_URL or INTEGRATION_API_URL from `/lib/config.ts`
- Import components import: importApi service module with typed functions
- Chart components import: chart type definitions from `/components/charts/types.ts`

### External Dependencies

#### Framework and Core
- **react** (18+): Core React library with hooks (useState, useEffect, useCallback, memo, useMemo)
- **react-dom** (18+): React DOM rendering
- **react-router-dom**: BrowserRouter, Routes, Route for client-side routing

#### UI and Styling
- **tailwindcss** (4.0+): Utility-first CSS framework for all styling
- **lucide-react**: Icon library (RefreshCw, AlertCircle, Brain, Shield, etc.)
- **react-grid-layout** (^1.3.5): Draggable, resizable grid layout system
- **react-resizable** (^3.0.4): Resizing component utilities

#### Data Visualization
- **recharts** (^2.10.0+): Composable charting library for React
  - Components: ComposedChart, AreaChart, LineChart, XAxis, YAxis, Tooltip, Area, Line, ResponsiveContainer

#### API and Data Fetching
- **fetch API** (Native browser): Used for all HTTP requests
- No third-party HTTP client library (using native fetch with JSON serialization)

#### Development and Testing
- **vitest**: Unit test framework
- **@testing-library/react**: React component testing utilities
- **@testing-library/user-event**: User interaction simulation
- **msw** (Mock Service Worker): API mocking for tests
- **typescript**: Type system and compilation
- **vite**: Build tool and development server

#### Package Management
- **npm/pnpm**: Dependency management (package.json in root directory)

## Relationships

### Component Hierarchy

```
App (root)
├── DashboardPage
│   ├── QueryInterface
│   └── DashboardGrid (react-grid-layout)
│       ├── InsightWidget (memoized)
│       ├── AnomalyWidget
│       │   └── useAnomalies() hook
│       ├── PredictionWidget (memoized)
│       └── ComplianceWidget
└── ImportDataPage
    └── ImportWizard
        ├── SourceSelectionStep
        ├── ConfigurationStep
        ├── PreviewStep
        └── ProgressStep
        └── HelpPanel
```

### Data Flow

```
User Input
  ↓
Component State (useState)
  ↓
useCallback/useEffect Handlers
  ↓
Fetch to API (analytics or integration)
  ↓
Response Parsing (JSON)
  ↓
State Update
  ↓
Component Re-render (with memoization)
  ↓
UI Display (Tailwind + Lucide icons)
```

### API Integration Points

```
Analytics API (ANALYTICS_API_URL: 8080)
├── GET /insights → InsightWidget
├── GET /anomalies → useAnomalies hook → AnomalyWidget
├── GET /compliance → ComplianceWidget
├── GET /predictions → PredictionWidget
└── POST /query → QueryInterface

Integration API (INTEGRATION_API_URL: 8100)
├── POST /api/imports/preview → ImportWizard.PreviewStep
├── POST /api/imports → ImportWizard.ProgressStep
├── GET /api/imports/{jobId} → ImportWizard.ProgressStep
├── GET /api/imports → ImportWizard
└── DELETE /api/imports/{jobId} → ImportWizard
```

### State Management Patterns

```
Local Component State (useState)
├── LoadingState (idle → loading → success/error)
├── Data State (null → data object)
├── Error State (null → error message)
└── UI State (filters, sorting, visibility toggles)

Derived/Computed State (useMemo)
├── Color classes from severity levels
├── Formatted timestamps and data
└── Chart data transformations

Stable Callback References (useCallback)
├── API fetch functions (prevents infinite useEffect loops)
├── Event handlers
└── Filter/sort handlers
```

### Module Dependencies Graph

```
mermaid
graph TD
    App[App.tsx]
    DashboardPage[DashboardPage]
    ImportPage[ImportDataPage]
    DashboardGrid[DashboardGrid]
    QueryInterface[QueryInterface]

    InsightWidget[InsightWidget]
    AnomalyWidget[AnomalyWidget]
    PredictionWidget[PredictionWidget]
    ComplianceWidget[ComplianceWidget]

    useAnomalies[useAnomalies Hook]
    LoadingOverlay[LoadingOverlay]
    Tooltip[Tooltip]

    Config[lib/config.ts]
    Types[lib/types.ts]
    AnomalyTypes[types/anomalies.ts]
    ImportApi[services/importApi.ts]

    App -->|routes| DashboardPage
    App -->|routes| ImportPage

    DashboardPage --> QueryInterface
    DashboardPage --> DashboardGrid

    DashboardGrid --> InsightWidget
    DashboardGrid --> AnomalyWidget
    DashboardGrid --> PredictionWidget
    DashboardGrid --> ComplianceWidget
    DashboardGrid --> Tooltip

    AnomalyWidget --> useAnomalies
    AnomalyWidget --> AnomalyTypes

    InsightWidget --> Config
    AnomalyWidget --> Config
    ComplianceWidget --> Config
    QueryInterface --> Config

    useAnomalies --> Config
    useAnomalies --> AnomalyTypes

    ComplianceWidget --> Types
    InsightWidget --> Types
    AnomalyWidget --> Types
    QueryInterface --> Types
    PredictionWidget --> Types

    ImportPage --> ImportApi
    ImportApi --> Config
```

## Architecture Patterns

### Component Patterns

#### Memoized Data-Fetching Widgets
- **Pattern**: `React.memo()` wrapping function components with `useCallback()` for fetch functions
- **Examples**: InsightWidget, PredictionWidget
- **Benefit**: Prevents re-renders when parent dashboard updates other widgets
- **Trade-off**: Component has no props, so memoization is effective

#### Controlled Filtering Pattern
- **Pattern**: Local state (filter value) + dependency on filter in fetch + useEffect refetch
- **Examples**: AnomalyWidget (severityFilter), ComplianceWidget (severityFilter)
- **Flow**: User clicks filter → setState → useEffect triggers fetchData(severityFilter) → setData
- **Benefit**: Real-time filtering without page reload

#### Loading State Pattern
- **Pattern**: Conditional rendering based on LoadingState union type
- **States**: idle, loading, success, error
- **Benefits**:
  - Explicit state machine (no impossible states)
  - Graceful error handling with retry buttons
  - Loading skeletons for better UX

#### localStorage Persistence Pattern
- **Pattern**: Save state to localStorage on change, restore on mount
- **Example**: DashboardGrid layout persistence
- **Implementation**:
  1. Load from localStorage on initial render
  2. Save to localStorage on every layout change
  3. Validate on load, reset to defaults if invalid
- **Benefit**: User layouts persist across sessions

### Hook Patterns

#### Data-Fetching Hook Pattern
- **Pattern**: Custom hook returns { data, loading, error, refetch }
- **Example**: useAnomalies hook
- **Benefits**:
  - Reusable data-fetching logic
  - Consistent error handling
  - Manual refresh capability
  - Can be tested independently

#### Dependency Injection via Props
- **Pattern**: Widget components don't directly import hooks, they use props or expose hooks to consumers
- **Example**: AnomalyWidget uses useAnomalies but separates hook logic
- **Benefit**: Testability - can mock hook responses

### API Integration Patterns

#### Typed API Client Module
- **Pattern**: Service module (importApi.ts) exports typed functions with full request/response types
- **Benefits**:
  - Type safety for API contracts
  - Custom error class (ImportApiError)
  - Error handling centralized
  - Functions can be tested without mocking fetch

#### URL Building Pattern
- **Pattern**: Use `new URL()` API for building URLs with query parameters
- **Example**: `const url = new URL(\`${API_BASE_URL}/anomalies\`); if (filter) url.searchParams.set(...)`
- **Benefit**: Type-safe query parameter building

### UI Patterns

#### Tailwind Multi-line CSS Classes
- **Pattern**: Responsive classes split across multiple lines, smallest breakpoint first
- **Examples** (from code-style.md):
  ```
  className="custom-cta bg-gray-50 p-4 rounded
             hover:bg-gray-100
             xs:p-6
             sm:p-8 sm:font-medium
             md:p-10 md:text-lg"
  ```
- **Benefit**: Readability of complex responsive designs

#### Icon + Text + Badge Pattern
- **Pattern**: Combine Lucide icon + text label + optional badge in header
- **Examples**: Widget headers, severity indicators
- **Structure**: `<Icon/> <Title/> <Badge/>`

#### Progress Indicator Pattern
- **Pattern**: Horizontal progress bar with percentage text
- **Examples**: Compliance score bar in ComplianceWidget, anomaly severity bar
- **Implementation**: HTML div with width percentage based on data value

## Code Quality Metrics

### Memoization Strategy
- **Level**: Component-level (React.memo) + function-level (useCallback)
- **Effectiveness**: High for dashboard with multiple independent widgets
- **Coverage**: InsightWidget, PredictionWidget use memo; all data-fetch functions use useCallback

### Error Handling
- **Pattern**: try/catch in fetch functions, state-based error display
- **Coverage**: All API calls wrapped in try/catch
- **UX**: Error messages displayed with retry buttons

### Type Safety
- **Level**: Full TypeScript with explicit interfaces for all API responses
- **Coverage**: All external API data has explicit types
- **Benefits**: Compile-time checking of API contract mismatches

### Testing Coverage
- **Unit Tests**: Components, hooks, utilities (10+ test files)
- **Integration Tests**: API integration with MSW mocks
- **E2E Tests**: Dashboard verification scripts
- **Test Tools**: Vitest, Testing Library, MSW

### Performance Optimizations

#### 1. Memoization
- Components wrapped with React.memo to prevent unnecessary re-renders
- useCallback for stable function references

#### 2. localStorage Persistence
- Avoids re-computing complex layouts
- Instant page load experience

#### 3. Lazy Loading
- Widgets load data independently via fetch
- One widget's failure doesn't block others

#### 4. Responsive Layouts
- CSS-based responsive design (Tailwind)
- No JavaScript recalculation on resize (react-grid-layout handles it)

#### 5. Code Splitting Opportunities
- Different pages (Dashboard vs ImportData) could be split
- Chart libraries imported on-demand

## Development Guidelines

### Adding New Widgets
1. Create component file in `/components/widgets/`
2. Extend from existing widget pattern (LoadingState, error handling)
3. Add to WIDGET_CONFIGS array in DashboardGrid
4. Add responsive layout configuration for all breakpoints
5. Add tests in `__tests__/` subdirectory

### Adding New API Endpoints
1. Define request/response types in `/types/` or service module
2. Create fetch function in service module or component
3. Use in hook or component with LoadingState pattern
4. Add MSW mock handler in `/test/mocks/handlers.ts`
5. Test with integration test

### Styling Guidelines
1. Use Tailwind CSS utility classes
2. Follow responsive-first pattern (no prefix → xs → sm → md → lg → xl → 2xl)
3. Use lucide-react icons for consistency
4. Define color themes: red (critical), orange (high), yellow (medium), blue (low), green (success)
5. Maintain consistent spacing with base 4px grid (p-1, p-2, p-3, p-4, etc.)

## File Organization

```
src/
├── App.tsx                          # Root router component
├── main.tsx                         # Entry point
├── index.css                        # Global styles
├── lib/
│   ├── config.ts                    # API configuration
│   ├── types.ts                     # Shared types (LoadingState)
│   └── index.ts                     # Barrel export
├── types/
│   └── anomalies.ts                 # Anomaly data types
├── hooks/
│   ├── useAnomalies.ts              # Anomaly data hook
│   ├── types.ts                     # Hook type definitions
│   └── index.ts                     # Barrel export
├── services/
│   └── importApi.ts                 # Import API client
├── layouts/
│   ├── DashboardGrid.tsx            # Main dashboard layout
│   └── __tests__/
│       └── DashboardGrid.test.tsx
├── components/
│   ├── QueryInterface.tsx           # Natural language query
│   ├── LoadingOverlay.tsx           # Loading overlay component
│   ├── SkipLink.tsx                 # Accessibility component
│   ├── common/
│   │   ├── Tooltip.tsx              # Reusable tooltip
│   │   ├── index.ts
│   │   └── __tests__/
│   │       └── Tooltip.test.tsx
│   ├── widgets/
│   │   ├── InsightWidget.tsx        # AI insights
│   │   ├── AnomalyWidget.tsx        # Anomaly detection
│   │   ├── ComplianceWidget.tsx     # Compliance status
│   │   ├── PredictionWidget.tsx     # Violation forecast
│   │   ├── index.ts
│   │   └── __tests__/
│   │       ├── InsightWidget.test.tsx
│   │       ├── AnomalyWidget.test.tsx
│   │       ├── ComplianceWidget.test.tsx
│   │       └── PredictionWidget.test.tsx
│   ├── charts/
│   │   ├── AreaChart.tsx
│   │   ├── LineChart.tsx
│   │   ├── ComposedChart.tsx
│   │   ├── ResponsiveChart.tsx
│   │   ├── types.ts
│   │   └── index.ts
│   ├── ImportWizard/
│   │   ├── ImportWizard.tsx         # Main wizard component
│   │   ├── SourceSelectionStep.tsx
│   │   ├── ConfigurationStep.tsx
│   │   ├── PreviewStep.tsx
│   │   ├── ProgressStep.tsx
│   │   └── HelpPanel.tsx
│   └── __tests__/
│       └── QueryInterface.test.tsx
├── pages/
│   └── ImportDataPage.tsx           # Import page
└── test/
    ├── setupTests.ts                # Test environment setup
    ├── hooks/
    │   └── useAnomalies.test.ts
    ├── integration/
    │   └── dashboard_api_integration.test.tsx
    ├── e2e/
    │   └── verify_dashboard_integration.ts
    └── mocks/
        ├── handlers.ts              # MSW request handlers
        └── server.ts                # MSW server setup
```

## Notes

- **Browser Storage**: Dashboard layout persists to localStorage under key "acgs-analytics-dashboard-layout"
- **API Timeout**: No explicit timeout configured; relies on browser defaults (varies by browser, typically 30-60 seconds)
- **Error Recovery**: All widgets implement retry buttons for failed API calls
- **Responsive Design**: 5 breakpoints (xxs: 0, xs: 480, sm: 768, md: 996, lg: 1200)
- **Performance**: Dashboard Grid uses CSS transforms for smooth dragging performance
- **Accessibility**: ARIA labels, skip links, keyboard navigation support (Grid layout library handles keyboard)
- **Theme Colors**:
  - Indigo (primary): #4f46e5
  - Red (critical): #dc2626
  - Orange (high): #ea580c
  - Yellow (medium): #eab308
  - Blue (low): #2563eb
  - Green (success): #16a34a
  - Gray (neutral): #6b7280
- **Widget Sizing**: Minimum widths/heights enforced to prevent overly small widgets, configurable per breakpoint
- **Import System**: Supports JIRA, ServiceNow, GitHub, GitLab with source-specific configuration
- **Natural Language**: Query interface uses simple keyword matching; backend handles NLU
- **Caching**: Insights endpoint supports cache bypass via `refresh=true` parameter
- **Model Status**: Anomaly and Prediction widgets track whether ML models are trained
