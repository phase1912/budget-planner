import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Modal, ModalHeader, ModalBody, ModalFooter } from "./Modal";

describe("Modal", () => {
  it("renders when isOpen is true and calls onClose", () => {
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose}>
        <ModalHeader>Title</ModalHeader>
        <ModalBody>Content</ModalBody>
        <ModalFooter>Footer</ModalFooter>
      </Modal>,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Title")).toBeInTheDocument();

    // Click backdrop
    fireEvent.click(screen.getByTestId("backdrop"));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("does not render when isOpen is false", () => {
    render(
      <Modal isOpen={false} onClose={vi.fn()}>
        <div data-testid="content">Content</div>
      </Modal>,
    );
    expect(screen.queryByTestId("content")).not.toBeInTheDocument();
  });
});

describe("Modal focus management", () => {
  it("moves focus into the dialog when it opens", () => {
    render(
      <Modal isOpen={true} onClose={vi.fn()}>
        <ModalBody>
          <button>Inside</button>
        </ModalBody>
      </Modal>,
    );

    expect(screen.getByRole("dialog")).toHaveFocus();
  });

  it("keeps Tab inside the dialog", () => {
    render(
      <Modal isOpen={true} onClose={vi.fn()}>
        <ModalBody>
          <button>First</button>
          <button>Last</button>
        </ModalBody>
      </Modal>,
    );

    const first = screen.getByText("First");
    const last = screen.getByText("Last");

    last.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(first).toHaveFocus();

    first.focus();
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(last).toHaveFocus();
  });

  it("returns focus to whatever opened it", () => {
    const trigger = document.createElement("button");
    document.body.appendChild(trigger);
    trigger.focus();

    const { rerender } = render(
      <Modal isOpen={true} onClose={vi.fn()}>
        <ModalBody>
          <button>Inside</button>
        </ModalBody>
      </Modal>,
    );

    rerender(
      <Modal isOpen={false} onClose={vi.fn()}>
        <ModalBody>
          <button>Inside</button>
        </ModalBody>
      </Modal>,
    );

    expect(trigger).toHaveFocus();
    trigger.remove();
  });
});
