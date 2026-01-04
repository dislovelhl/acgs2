/**
 * Tooltip Component Tests
 *
 * Tests for the Tooltip component including:
 * - Basic rendering with children
 * - Positioning logic (top, bottom, left, right)
 * - Accessibility (ARIA attributes, keyboard support)
 * - Hover interactions and delays
 * - Focus interactions
 * - Edge cases (disabled state, custom delays, cleanup)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Tooltip } from "../Tooltip";

describe("Tooltip", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  describe("Rendering", () => {
    it("renders children without tooltip initially", () => {
      render(
        <Tooltip content="Help text">
          <button>Click me</button>
        </Tooltip>
      );

      expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument();
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    });

    it("renders tooltip content on hover after delay", async () => {
      render(
        <Tooltip content="Help text" delay={200}>
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button", { name: "Hover me" });

      // Hover over the button
      await userEvent.hover(button);

      // Tooltip should not appear immediately
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

      // Advance timers to trigger tooltip
      vi.advanceTimersByTime(200);

      // Tooltip should now be visible
      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });
      expect(screen.getByText("Help text")).toBeInTheDocument();
    });

    it("renders ReactNode content", async () => {
      const ComplexContent = () => (
        <div>
          <strong>Bold text</strong>
          <span> and regular text</span>
        </div>
      );

      render(
        <Tooltip content={<ComplexContent />}>
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        expect(screen.getByText("Bold text")).toBeInTheDocument();
      });
      expect(screen.getByText("and regular text")).toBeInTheDocument();
    });

    it("applies custom className to tooltip", async () => {
      render(
        <Tooltip content="Help text" className="custom-tooltip-class">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        const tooltip = screen.getByRole("tooltip");
        expect(tooltip).toHaveClass("custom-tooltip-class");
      });
    });
  });

  describe("Positioning", () => {
    it("positions tooltip on top by default", async () => {
      render(
        <Tooltip content="Help text">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        const tooltip = screen.getByRole("tooltip");
        // Check for top positioning classes
        expect(tooltip).toHaveClass("bottom-full");
      });
    });

    it("positions tooltip on bottom when specified", async () => {
      render(
        <Tooltip content="Help text" position="bottom">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        const tooltip = screen.getByRole("tooltip");
        expect(tooltip).toHaveClass("top-full");
      });
    });

    it("positions tooltip on left when specified", async () => {
      render(
        <Tooltip content="Help text" position="left">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        const tooltip = screen.getByRole("tooltip");
        expect(tooltip).toHaveClass("right-full");
      });
    });

    it("positions tooltip on right when specified", async () => {
      render(
        <Tooltip content="Help text" position="right">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        const tooltip = screen.getByRole("tooltip");
        expect(tooltip).toHaveClass("left-full");
      });
    });

    it("renders arrow in correct position for top tooltip", async () => {
      render(
        <Tooltip content="Help text" position="top">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        const tooltip = screen.getByRole("tooltip");
        const arrow = tooltip.querySelector('[aria-hidden="true"]');
        expect(arrow).toHaveClass("-bottom-1");
      });
    });

    it("renders arrow in correct position for bottom tooltip", async () => {
      render(
        <Tooltip content="Help text" position="bottom">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        const tooltip = screen.getByRole("tooltip");
        const arrow = tooltip.querySelector('[aria-hidden="true"]');
        expect(arrow).toHaveClass("-top-1");
      });
    });
  });

  describe("Accessibility", () => {
    it("has role='tooltip' attribute", async () => {
      render(
        <Tooltip content="Help text">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });
    });

    it("links trigger to tooltip with aria-describedby", async () => {
      render(
        <Tooltip content="Help text">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");

      // Before hover, no aria-describedby
      expect(button.parentElement?.getAttribute("aria-describedby")).toBeNull();

      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        const tooltip = screen.getByRole("tooltip");
        const tooltipId = tooltip.id;
        expect(button.parentElement?.getAttribute("aria-describedby")).toBe(tooltipId);
      });
    });

    it("removes aria-describedby when tooltip is hidden", async () => {
      render(
        <Tooltip content="Help text">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");

      // Hover to show
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });

      // Unhover to hide
      await userEvent.unhover(button);

      await waitFor(() => {
        expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      });

      expect(button.parentElement?.getAttribute("aria-describedby")).toBeNull();
    });

    it("shows tooltip on keyboard focus", async () => {
      render(
        <Tooltip content="Help text">
          <button>Focus me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");

      // Focus the button
      button.focus();
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });
    });

    it("hides tooltip on blur", async () => {
      render(
        <Tooltip content="Help text">
          <button>Focus me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");

      // Focus to show
      button.focus();
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });

      // Blur to hide
      button.blur();

      await waitFor(() => {
        expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      });
    });

    it("uses unique IDs for multiple tooltips", async () => {
      render(
        <div>
          <Tooltip content="First tooltip">
            <button>Button 1</button>
          </Tooltip>
          <Tooltip content="Second tooltip">
            <button>Button 2</button>
          </Tooltip>
        </div>
      );

      const [button1, button2] = screen.getAllByRole("button");

      // Show both tooltips
      await userEvent.hover(button1);
      await userEvent.hover(button2);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        const tooltips = screen.getAllByRole("tooltip");
        expect(tooltips).toHaveLength(2);

        // IDs should be unique
        expect(tooltips[0].id).not.toBe(tooltips[1].id);
      });
    });
  });

  describe("Hover Interactions", () => {
    it("respects custom show delay", async () => {
      render(
        <Tooltip content="Help text" delay={500}>
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);

      // Should not show after 200ms
      vi.advanceTimersByTime(200);
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

      // Should show after 500ms
      vi.advanceTimersByTime(300);
      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });
    });

    it("shows immediately with delay={0}", async () => {
      render(
        <Tooltip content="Help text" delay={0}>
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(0);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });
    });

    it("hides immediately by default when unhovered", async () => {
      render(
        <Tooltip content="Help text">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");

      // Show tooltip
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });

      // Unhover
      await userEvent.unhover(button);

      await waitFor(() => {
        expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      });
    });

    it("respects custom hide delay", async () => {
      render(
        <Tooltip content="Help text" hideDelay={300}>
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");

      // Show tooltip
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });

      // Unhover
      await userEvent.unhover(button);

      // Should still be visible after 100ms
      vi.advanceTimersByTime(100);
      expect(screen.getByRole("tooltip")).toBeInTheDocument();

      // Should hide after 300ms
      vi.advanceTimersByTime(200);
      await waitFor(() => {
        expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      });
    });

    it("cancels show timeout on quick unhover", async () => {
      render(
        <Tooltip content="Help text" delay={500}>
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");

      // Hover
      await userEvent.hover(button);

      // Quickly unhover before delay completes
      vi.advanceTimersByTime(200);
      await userEvent.unhover(button);

      // Complete the original delay time
      vi.advanceTimersByTime(300);

      // Tooltip should never appear
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    });

    it("cancels hide timeout on quick re-hover", async () => {
      render(
        <Tooltip content="Help text" hideDelay={300}>
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");

      // Show tooltip
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });

      // Start hiding
      await userEvent.unhover(button);
      vi.advanceTimersByTime(100);

      // Re-hover before hide completes
      await userEvent.hover(button);
      vi.advanceTimersByTime(300);

      // Tooltip should still be visible
      expect(screen.getByRole("tooltip")).toBeInTheDocument();
    });
  });

  describe("Disabled State", () => {
    it("does not show tooltip when disabled", async () => {
      render(
        <Tooltip content="Help text" disabled={true}>
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    });

    it("does not show tooltip on focus when disabled", async () => {
      render(
        <Tooltip content="Help text" disabled={true}>
          <button>Focus me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      button.focus();
      vi.advanceTimersByTime(200);

      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    });

    it("hides tooltip immediately when disabled prop changes to true", async () => {
      const { rerender } = render(
        <Tooltip content="Help text" disabled={false}>
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");

      // Show tooltip
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });

      // Change to disabled
      rerender(
        <Tooltip content="Help text" disabled={true}>
          <button>Hover me</button>
        </Tooltip>
      );

      // Tooltip should be hidden
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("handles empty string content", async () => {
      render(
        <Tooltip content="">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });
    });

    it("cleans up timeouts on unmount", () => {
      const clearTimeoutSpy = vi.spyOn(window, "clearTimeout");

      const { unmount } = render(
        <Tooltip content="Help text">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      button.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));

      // Unmount before timeout completes
      unmount();

      // Should have cleared timeout
      expect(clearTimeoutSpy).toHaveBeenCalled();

      clearTimeoutSpy.mockRestore();
    });

    it("handles rapid hover/unhover cycles", async () => {
      render(
        <Tooltip content="Help text" delay={200}>
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");

      // Rapid hover/unhover
      for (let i = 0; i < 5; i++) {
        await userEvent.hover(button);
        vi.advanceTimersByTime(50);
        await userEvent.unhover(button);
        vi.advanceTimersByTime(50);
      }

      // Tooltip should not be visible
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    });

    it("maintains tooltip state during multiple children interactions", async () => {
      render(
        <Tooltip content="Help text">
          <div>
            <button>Button 1</button>
            <button>Button 2</button>
          </div>
        </Tooltip>
      );

      const [button1, button2] = screen.getAllByRole("button");

      // Hover over the parent container
      await userEvent.hover(button1);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });

      // Click second button (still within tooltip trigger area)
      await userEvent.click(button2);

      // Tooltip should still be visible
      expect(screen.getByRole("tooltip")).toBeInTheDocument();
    });

    it("works with non-interactive children", async () => {
      render(
        <Tooltip content="Help text">
          <span>Hover text</span>
        </Tooltip>
      );

      const span = screen.getByText("Hover text");
      await userEvent.hover(span);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });
    });

    it("renders with all position and delay combinations", async () => {
      const positions = ["top", "bottom", "left", "right"] as const;
      const delays = [0, 100, 500];

      for (const position of positions) {
        for (const delay of delays) {
          const { unmount } = render(
            <Tooltip content={`${position}-${delay}`} position={position} delay={delay}>
              <button>Test</button>
            </Tooltip>
          );

          const button = screen.getByRole("button");
          await userEvent.hover(button);
          vi.advanceTimersByTime(delay);

          await waitFor(() => {
            expect(screen.getByRole("tooltip")).toBeInTheDocument();
          });

          unmount();
        }
      }
    });
  });

  describe("Styling", () => {
    it("applies base tooltip styles", async () => {
      render(
        <Tooltip content="Help text">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        const tooltip = screen.getByRole("tooltip");
        expect(tooltip).toHaveClass("absolute");
        expect(tooltip).toHaveClass("z-50");
      });
    });

    it("renders arrow with correct styling", async () => {
      render(
        <Tooltip content="Help text">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        const tooltip = screen.getByRole("tooltip");
        const arrow = tooltip.querySelector('[aria-hidden="true"]');
        expect(arrow).toHaveClass("rotate-45");
        expect(arrow).toHaveClass("bg-gray-900");
      });
    });

    it("renders content container with proper styling", async () => {
      render(
        <Tooltip content="Help text">
          <button>Hover me</button>
        </Tooltip>
      );

      const button = screen.getByRole("button");
      await userEvent.hover(button);
      vi.advanceTimersByTime(200);

      await waitFor(() => {
        const tooltip = screen.getByRole("tooltip");
        const content = tooltip.querySelector(".rounded-md");
        expect(content).toHaveClass("bg-gray-900");
        expect(content).toHaveClass("text-white");
        expect(content).toHaveClass("shadow-lg");
      });
    });
  });
});
