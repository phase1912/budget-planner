import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "./Table";

describe("Table", () => {
  it("renders table elements with correct roles", () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Col 1</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Row 1</TableCell>
          </TableRow>
        </TableBody>
      </Table>,
    );
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Col 1" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Row 1" })).toBeInTheDocument();
  });
});
