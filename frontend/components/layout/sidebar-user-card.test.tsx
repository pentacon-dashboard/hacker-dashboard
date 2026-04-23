import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SidebarUserCard } from "./sidebar-user-card";

describe("SidebarUserCard", () => {
  it("펼침 상태에서 Demo User 이름을 렌더한다", () => {
    render(<SidebarUserCard collapsed={false} />);
    expect(screen.getByText("Demo User")).toBeInTheDocument();
  });

  it("펼침 상태에서 이메일을 렌더한다", () => {
    render(<SidebarUserCard collapsed={false} />);
    expect(screen.getByText("demo@demo.com")).toBeInTheDocument();
  });

  it("접힘 상태에서 이름/이메일이 없어야 한다", () => {
    render(<SidebarUserCard collapsed={true} />);
    expect(screen.queryByText("Demo User")).not.toBeInTheDocument();
    expect(screen.queryByText("demo@demo.com")).not.toBeInTheDocument();
  });
});
