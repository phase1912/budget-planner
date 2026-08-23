import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Container, Stack, Grid } from "./Layout";

describe("Layout", () => {
  it("renders Container, Stack, and Grid", () => {
    render(
      <Container data-testid="container">
        <Stack data-testid="stack">
          <Grid data-testid="grid">
            <div>Item</div>
          </Grid>
        </Stack>
      </Container>,
    );
    expect(screen.getByTestId("container")).toBeInTheDocument();
    expect(screen.getByTestId("stack")).toBeInTheDocument();
    expect(screen.getByTestId("grid")).toBeInTheDocument();
  });
});
