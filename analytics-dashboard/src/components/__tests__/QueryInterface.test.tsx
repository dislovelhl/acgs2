/**
 * QueryInterface Component Tests
 *
 * Tests for the QueryInterface component including:
 * - Natural language query input
 * - Query submission and response display
 * - Sample query suggestions
 * - Query history tracking
 * - Error handling
 * - Integration with analytics-api /query endpoint
 */

import { describe, it, expect } from "vitest";
import {
  render,
  screen,
  waitFor,
  fireEvent,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../test/mocks/server";
import { errorHandlers } from "../../test/mocks/handlers";
import { QueryInterface } from "../QueryInterface";

const API_BASE_URL = "http://localhost:8080";

describe("QueryInterface", () => {
  describe("Initial Render", () => {
    it("renders header and input field", () => {
      render(<QueryInterface />);

      expect(screen.getByText("Ask About Governance")).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText(/Ask a question about governance data/i)
      ).toBeInTheDocument();
    });

    it("shows sample query suggestions", () => {
      render(<QueryInterface />);

      expect(screen.getByText("Try asking:")).toBeInTheDocument();
      expect(
        screen.getByText("Show violations this week")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Which policy is violated most?")
      ).toBeInTheDocument();
    });

    it("has a submit button", () => {
      render(<QueryInterface />);

      expect(screen.getByRole("button", { name: /ask/i })).toBeInTheDocument();
    });
  });

  describe("Query Input", () => {
    it("updates input value when typing", async () => {
      const user = userEvent.setup();
      render(<QueryInterface />);

      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "How many violations today?");

      expect(input).toHaveValue("How many violations today?");
    });

    it("submits query on form submission", async () => {
      const user = userEvent.setup();
      render(<QueryInterface />);

      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "Show violations this week");

      const submitButton = screen.getByRole("button", { name: /ask/i });
      await user.click(submitButton);

      // Wait for response
      await waitFor(() => {
        expect(screen.getByText("Answer")).toBeInTheDocument();
      });
    });

    it("disables submit button when input is empty", () => {
      render(<QueryInterface />);

      const submitButton = screen.getByRole("button", { name: /ask/i });
      expect(submitButton).toBeDisabled();
    });

    it("enables submit button when input has text", async () => {
      const user = userEvent.setup();
      render(<QueryInterface />);

      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "Test query");

      const submitButton = screen.getByRole("button", { name: /ask/i });
      expect(submitButton).toBeEnabled();
    });
  });

  describe("Sample Queries", () => {
    it("submits sample query when clicked", async () => {
      const user = userEvent.setup();
      render(<QueryInterface />);

      const sampleQuery = screen.getByText("Show violations this week");
      await user.click(sampleQuery);

      // Wait for response
      await waitFor(() => {
        expect(screen.getByText("Answer")).toBeInTheDocument();
      });
    });

    it("hides sample queries after submitting", async () => {
      const user = userEvent.setup();
      render(<QueryInterface />);

      const sampleQuery = screen.getByText("Show violations this week");
      await user.click(sampleQuery);

      await waitFor(() => {
        expect(screen.queryByText("Try asking:")).not.toBeInTheDocument();
      });
    });
  });

  describe("Query Response Display", () => {
    it("displays answer from API response", async () => {
      const user = userEvent.setup();
      render(<QueryInterface />);

      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "Show violations this week");

      const submitButton = screen.getByRole("button", { name: /ask/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/There were 23 policy violations this week/)
        ).toBeInTheDocument();
      });
    });

    it("displays related data from API response", async () => {
      const user = userEvent.setup();
      render(<QueryInterface />);

      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "Show violations this week");

      const submitButton = screen.getByRole("button", { name: /ask/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText("Related Data")).toBeInTheDocument();
        expect(screen.getByText(/total violations:/i)).toBeInTheDocument();
      });
    });

    it("shows warning when query not fully understood", async () => {
      server.use(
        http.post(`${API_BASE_URL}/query`, async ({ request }) => {
          const body = await request.json();
          const question =
            typeof body === "object" && body !== null && "question" in body
              ? (body as { question: string }).question
              : "";

          return HttpResponse.json({
            query: question,
            answer: "I could not fully understand your query.",
            data: {},
            query_understood: false,
            generated_at: new Date().toISOString(),
          });
        })
      );

      const user = userEvent.setup();
      render(<QueryInterface />);

      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "xyzabc random text");

      const submitButton = screen.getByRole("button", { name: /ask/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/Could not fully understand your query/)
        ).toBeInTheDocument();
      });
    });
  });

  describe("Query History", () => {
    it("tracks query history", async () => {
      const user = userEvent.setup();
      render(<QueryInterface />);

      // Submit first query
      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "First query");
      await user.click(screen.getByRole("button", { name: /ask/i }));

      await waitFor(() => {
        expect(screen.getByText("Answer")).toBeInTheDocument();
      });

      // Click Ask Another Question
      await user.click(screen.getByText("Ask Another Question"));

      // Submit second query
      await user.type(input, "Second query");
      await user.click(screen.getByRole("button", { name: /ask/i }));

      await waitFor(() => {
        expect(screen.getByText(/Recent queries \(2\)/)).toBeInTheDocument();
      });
    });

    it("can restore previous query from history", async () => {
      const user = userEvent.setup();
      render(<QueryInterface />);

      // Submit a query
      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "Show violations this week");
      await user.click(screen.getByRole("button", { name: /ask/i }));

      await waitFor(() => {
        expect(screen.getByText("Answer")).toBeInTheDocument();
      });

      // Click Ask Another
      await user.click(screen.getByText("Ask Another Question"));

      // Expand history
      const historyToggle = screen.getByText(/Recent queries/);
      await user.click(historyToggle);

      // Click history item
      const historyItem = screen.getByText("Show violations this week");
      await user.click(historyItem);

      // Should restore the response
      await waitFor(() => {
        expect(screen.getByText("Answer")).toBeInTheDocument();
      });
    });
  });

  describe("Loading State", () => {
    it("shows loading spinner during query processing", async () => {
      const user = userEvent.setup();
      render(<QueryInterface />);

      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "Test query");
      await user.click(screen.getByRole("button", { name: /ask/i }));

      expect(
        screen.getByText("Processing your query...")
      ).toBeInTheDocument();
    });

    it("disables submit button during loading", async () => {
      const user = userEvent.setup();
      render(<QueryInterface />);

      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "Test query");

      const submitButton = screen.getByRole("button", { name: /ask/i });
      await user.click(submitButton);

      expect(submitButton).toBeDisabled();
    });
  });

  describe("Error Handling", () => {
    it("displays error message when query fails", async () => {
      server.use(errorHandlers.queryError);

      const user = userEvent.setup();
      render(<QueryInterface />);

      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "Test query");
      await user.click(screen.getByRole("button", { name: /ask/i }));

      await waitFor(() => {
        expect(screen.getByText("Query Failed")).toBeInTheDocument();
        expect(
          screen.getByText(/Query processing failed/)
        ).toBeInTheDocument();
      });
    });

    it("shows retry button on error", async () => {
      server.use(errorHandlers.queryError);

      const user = userEvent.setup();
      render(<QueryInterface />);

      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "Test query");
      await user.click(screen.getByRole("button", { name: /ask/i }));

      await waitFor(() => {
        expect(screen.getByText("Try Again")).toBeInTheDocument();
      });
    });
  });

  describe("Clear Functionality", () => {
    it("clears input and response when Ask Another is clicked", async () => {
      const user = userEvent.setup();
      render(<QueryInterface />);

      const input = screen.getByPlaceholderText(
        /Ask a question about governance data/i
      );
      await user.type(input, "Show violations this week");
      await user.click(screen.getByRole("button", { name: /ask/i }));

      await waitFor(() => {
        expect(screen.getByText("Answer")).toBeInTheDocument();
      });

      await user.click(screen.getByText("Ask Another Question"));

      // Input should be cleared
      expect(input).toHaveValue("");

      // Sample queries should be visible again
      expect(screen.getByText("Try asking:")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has proper label for input field", () => {
      render(<QueryInterface />);

      const input = screen.getByRole("textbox", { name: /query input/i });
      expect(input).toBeInTheDocument();
    });

    it("has accessible submit button", () => {
      render(<QueryInterface />);

      expect(
        screen.getByRole("button", { name: /submit query/i })
      ).toBeInTheDocument();
    });
  });
});
