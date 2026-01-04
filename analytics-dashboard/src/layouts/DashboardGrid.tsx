/**
 * DashboardGrid Component
 *
 * Implements a customizable dashboard layout using react-grid-layout.
 * Features:
 * - Drag-and-drop widget repositioning
 * - Responsive layouts for different screen sizes
 * - localStorage persistence for user layouts
 * - Automatic grid layout with widget placeholders
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Responsive, WidthProvider, Layout, Layouts } from "react-grid-layout";
import { GripVertical, Lock, RotateCcw, Unlock } from "lucide-react";

// Import required CSS for react-grid-layout
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

// Import widget components
import { InsightWidget } from "../components/widgets/InsightWidget";
import { AnomalyWidget } from "../components/widgets/AnomalyWidget";
import { PredictionWidget } from "../components/widgets/PredictionWidget";
import { ComplianceWidget } from "../components/widgets/ComplianceWidget";
import { Tooltip } from "../components/common/Tooltip";

// Create responsive grid layout component
const ResponsiveGridLayout = WidthProvider(Responsive);

/** localStorage key for persisting layout */
const LAYOUT_STORAGE_KEY = "acgs-analytics-dashboard-layout";

/** Widget identifiers */
type WidgetId = "insights" | "anomalies" | "predictions" | "compliance";

/** Widget configuration */
interface WidgetConfig {
  id: WidgetId;
  title: string;
  component: React.ReactNode;
  defaultLayout: {
    x: number;
    y: number;
    w: number;
    h: number;
    minW?: number;
    minH?: number;
  };
}

/** Default widget configurations */
const WIDGET_CONFIGS: WidgetConfig[] = [
  {
    id: "insights",
    title: "AI Insights",
    component: <InsightWidget />,
    defaultLayout: { x: 0, y: 0, w: 6, h: 10, minW: 3, minH: 6 },
  },
  {
    id: "anomalies",
    title: "Anomaly Detection",
    component: <AnomalyWidget />,
    defaultLayout: { x: 6, y: 0, w: 6, h: 10, minW: 3, minH: 6 },
  },
  {
    id: "predictions",
    title: "Violation Forecast",
    component: <PredictionWidget />,
    defaultLayout: { x: 0, y: 10, w: 12, h: 12, minW: 6, minH: 8 },
  },
  {
    id: "compliance",
    title: "Compliance Status",
    component: <ComplianceWidget />,
    defaultLayout: { x: 0, y: 20, w: 6, h: 10, minW: 3, minH: 6 },
  },
];

/** Breakpoint definitions for responsive layouts */
const BREAKPOINTS = { lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 };

/** Column definitions per breakpoint */
const COLS = { lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 };

/** Row height in pixels */
const ROW_HEIGHT = 30;

/**
 * Generates default layouts for all breakpoints
 */
function generateDefaultLayouts(): Layouts {
  const layouts: Layouts = {};

  // Large screens (lg) - full 2-column layout
  layouts.lg = WIDGET_CONFIGS.map((widget) => ({
    i: widget.id,
    ...widget.defaultLayout,
  }));

  // Medium screens (md) - slightly condensed
  layouts.md = WIDGET_CONFIGS.map((widget) => ({
    i: widget.id,
    x: widget.id === "predictions" ? 0 : widget.defaultLayout.x === 0 ? 0 : 5,
    y: widget.defaultLayout.y,
    w: widget.id === "predictions" ? 10 : 5,
    h: widget.defaultLayout.h,
    minW: widget.defaultLayout.minW,
    minH: widget.defaultLayout.minH,
  }));

  // Small screens (sm) - stacked layout
  layouts.sm = WIDGET_CONFIGS.map((widget, index) => ({
    i: widget.id,
    x: 0,
    y: index * 10,
    w: 6,
    h: widget.id === "predictions" ? 12 : 10,
    minW: Math.min(widget.defaultLayout.minW || 3, 6),
    minH: widget.defaultLayout.minH,
  }));

  // Extra small screens (xs) - compact stacked layout
  layouts.xs = WIDGET_CONFIGS.map((widget, index) => ({
    i: widget.id,
    x: 0,
    y: index * 10,
    w: 4,
    h: widget.id === "predictions" ? 12 : 10,
    minW: Math.min(widget.defaultLayout.minW || 3, 4),
    minH: widget.defaultLayout.minH,
  }));

  // Tiny screens (xxs) - fully stacked
  layouts.xxs = WIDGET_CONFIGS.map((widget, index) => ({
    i: widget.id,
    x: 0,
    y: index * 12,
    w: 2,
    h: 12,
    minW: 2,
    minH: widget.defaultLayout.minH,
  }));

  return layouts;
}

/**
 * Saves layouts to localStorage
 */
function saveLayoutsToStorage(layouts: Layouts): void {
  try {
    localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(layouts));
  } catch (error) {
    // Handle localStorage errors gracefully (e.g., quota exceeded)
    if (error instanceof Error) {
      console.warn("Failed to save dashboard layout:", error.message);
    }
  }
}

/**
 * Loads layouts from localStorage with validation
 */
function loadLayoutsFromStorage(): Layouts | null {
  try {
    const storedLayouts = localStorage.getItem(LAYOUT_STORAGE_KEY);
    if (!storedLayouts) {
      return null;
    }

    const parsed = JSON.parse(storedLayouts);

    // Validate that parsed data is a valid Layouts object
    if (typeof parsed !== "object" || parsed === null) {
      console.warn("Invalid layout data in localStorage, resetting to default");
      localStorage.removeItem(LAYOUT_STORAGE_KEY);
      return null;
    }

    // Validate that each breakpoint contains valid layout arrays
    const validBreakpoints = Object.keys(BREAKPOINTS);
    for (const breakpoint of validBreakpoints) {
      if (parsed[breakpoint]) {
        if (!Array.isArray(parsed[breakpoint])) {
          console.warn(
            `Invalid layout for breakpoint ${breakpoint}, resetting to default`
          );
          localStorage.removeItem(LAYOUT_STORAGE_KEY);
          return null;
        }

        // Validate each layout item has required properties
        for (const item of parsed[breakpoint]) {
          if (
            typeof item.i !== "string" ||
            typeof item.x !== "number" ||
            typeof item.y !== "number" ||
            typeof item.w !== "number" ||
            typeof item.h !== "number"
          ) {
            console.warn(
              `Invalid layout item in ${breakpoint}, resetting to default`
            );
            localStorage.removeItem(LAYOUT_STORAGE_KEY);
            return null;
          }
        }
      }
    }

    return parsed as Layouts;
  } catch (error) {
    // Handle corrupted JSON or other parsing errors
    if (error instanceof Error) {
      console.warn(
        "Failed to parse dashboard layout from localStorage:",
        error.message
      );
    }
    localStorage.removeItem(LAYOUT_STORAGE_KEY);
    return null;
  }
}

/**
 * DashboardGrid - Main dashboard component with draggable/resizable widgets
 *
 * Features:
 * - Drag and drop widget repositioning
 * - Widget resizing
 * - Responsive layouts for different screen sizes
 * - Layout persistence to localStorage
 * - Layout lock toggle
 * - Reset to default layout
 */
export function DashboardGrid(): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [layouts, setLayouts] = useState<Layouts>(() => {
    // Try to load from storage, fall back to defaults
    return loadLayoutsFromStorage() || generateDefaultLayouts();
  });
  const [isLocked, setIsLocked] = useState(false);

  // Set mounted state after component mounts (prevents hydration issues)
  useEffect(() => {
    setMounted(true);
  }, []);

  /**
   * Handle layout changes from react-grid-layout
   * Persists new layouts to localStorage
   */
  const handleLayoutChange = useCallback(
    (currentLayout: Layout[], allLayouts: Layouts) => {
      setLayouts(allLayouts);
      saveLayoutsToStorage(allLayouts);
    },
    []
  );

  /**
   * Reset layouts to default configuration
   */
  const handleResetLayout = useCallback(() => {
    const defaultLayouts = generateDefaultLayouts();
    setLayouts(defaultLayouts);
    saveLayoutsToStorage(defaultLayouts);
  }, []);

  /**
   * Toggle layout lock state
   */
  const handleToggleLock = useCallback(() => {
    setIsLocked((prev) => !prev);
  }, []);

  // Don't render grid until mounted to prevent hydration mismatch
  if (!mounted) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"></div>
          <p className="mt-4 text-sm text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="dashboard-grid">
      {/* Dashboard Controls */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <GripVertical className="h-4 w-4" />
          <span>Drag widgets to rearrange</span>
        </div>
        <div className="flex items-center gap-2">
          <Tooltip
            content={
              isLocked ? (
                <div className="max-w-xs">
                  <strong>Layout Locked</strong>
                  <p className="mt-1 text-xs">
                    Widgets cannot be moved or resized. Click to unlock and
                    enable rearranging.
                  </p>
                </div>
              ) : (
                <div className="max-w-xs">
                  <strong>Layout Unlocked</strong>
                  <p className="mt-1 text-xs">
                    Widgets can be freely rearranged and resized. Click to lock
                    and prevent changes.
                  </p>
                </div>
              )
            }
            position="bottom"
          >
            <button
              onClick={handleToggleLock}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                isLocked
                  ? "bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
              title={isLocked ? "Unlock layout" : "Lock layout"}
              aria-label={isLocked ? "Unlock layout" : "Lock layout"}
            >
              {isLocked ? (
                <>
                  <Lock className="h-4 w-4" />
                  Locked
                </>
              ) : (
                <>
                  <Unlock className="h-4 w-4" />
                  Unlocked
                </>
              )}
            </button>
          </Tooltip>
          <button
            onClick={handleResetLayout}
            className="flex items-center gap-1.5 rounded-md bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-200"
            title="Reset to default layout"
            aria-label="Reset to default layout"
          >
            <RotateCcw className="h-4 w-4" />
            Reset Layout
          </button>
        </div>
      </div>

      {/* Responsive Grid Layout */}
      <ResponsiveGridLayout
        className="layout"
        layouts={layouts}
        breakpoints={BREAKPOINTS}
        cols={COLS}
        rowHeight={ROW_HEIGHT}
        onLayoutChange={handleLayoutChange}
        isDraggable={!isLocked}
        isResizable={!isLocked}
        draggableHandle=".widget-drag-handle"
        margin={[16, 16]}
        containerPadding={[0, 0]}
        useCSSTransforms={true}
        compactType="vertical"
        preventCollision={false}
      >
        {WIDGET_CONFIGS.map((widget) => (
          <div
            key={widget.id}
            className="widget-container relative overflow-hidden rounded-lg bg-white shadow-lg"
          >
            {/* Drag handle - only visible when layout is unlocked */}
            {!isLocked && (
              <div
                className="widget-drag-handle absolute left-0 right-0 top-0 z-10 flex cursor-move items-center justify-center bg-gradient-to-b from-gray-100 to-transparent py-1 opacity-0 transition-opacity hover:opacity-100"
                title={`Drag to move ${widget.title}`}
              >
                <div className="flex items-center gap-1 rounded-full bg-gray-200 px-2 py-0.5 text-xs text-gray-600">
                  <GripVertical className="h-3 w-3" />
                  <span>Drag</span>
                </div>
              </div>
            )}
            {/* Widget content */}
            <div className="h-full w-full">{widget.component}</div>
          </div>
        ))}
      </ResponsiveGridLayout>

      {/* Custom styles for grid layout */}
      <style>{`
        .react-grid-item {
          transition: all 200ms ease;
          transition-property: left, top;
        }
        .react-grid-item.cssTransforms {
          transition-property: transform;
        }
        .react-grid-item.resizing {
          z-index: 1;
          will-change: width, height;
        }
        .react-grid-item.react-draggable-dragging {
          transition: none;
          z-index: 3;
          will-change: transform;
        }
        .react-grid-item.dropping {
          visibility: hidden;
        }
        .react-grid-item.react-grid-placeholder {
          background: rgb(99 102 241 / 0.2);
          border-radius: 0.5rem;
          transition-duration: 100ms;
          z-index: 2;
          user-select: none;
        }
        .react-resizable-handle {
          position: absolute;
          width: 20px;
          height: 20px;
        }
        .react-resizable-handle::after {
          content: "";
          position: absolute;
          right: 4px;
          bottom: 4px;
          width: 8px;
          height: 8px;
          border-right: 2px solid rgba(0, 0, 0, 0.3);
          border-bottom: 2px solid rgba(0, 0, 0, 0.3);
        }
        .react-resizable-handle-sw {
          bottom: 0;
          left: 0;
          cursor: sw-resize;
          transform: rotate(90deg);
        }
        .react-resizable-handle-se {
          bottom: 0;
          right: 0;
          cursor: se-resize;
        }
        .react-resizable-handle-nw {
          top: 0;
          left: 0;
          cursor: nw-resize;
          transform: rotate(180deg);
        }
        .react-resizable-handle-ne {
          top: 0;
          right: 0;
          cursor: ne-resize;
          transform: rotate(270deg);
        }
        .react-resizable-handle-w,
        .react-resizable-handle-e {
          top: 50%;
          margin-top: -10px;
          cursor: ew-resize;
        }
        .react-resizable-handle-w {
          left: 0;
          transform: rotate(135deg);
        }
        .react-resizable-handle-e {
          right: 0;
          transform: rotate(315deg);
        }
        .react-resizable-handle-n,
        .react-resizable-handle-s {
          left: 50%;
          margin-left: -10px;
          cursor: ns-resize;
        }
        .react-resizable-handle-n {
          top: 0;
          transform: rotate(225deg);
        }
        .react-resizable-handle-s {
          bottom: 0;
          transform: rotate(45deg);
        }
        .widget-container:hover .widget-drag-handle {
          opacity: 1;
        }
      `}</style>
    </div>
  );
}

export default DashboardGrid;
