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
      </Modal>
    );
    
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Title")).toBeInTheDocument();
    
    // Click backdrop
    fireEvent.click(screen.getByTestId("backdrop"));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
  
  it("does not render when isOpen is false", () => {
    render(<Modal isOpen={false} onClose={vi.fn()}><div data-testid="content">Content</div></Modal>);
    expect(screen.queryByTestId("content")).not.toBeInTheDocument();
  });
});
