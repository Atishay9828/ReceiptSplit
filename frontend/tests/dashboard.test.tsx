import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/dashboard/page";
import { api } from "@/lib/api";
import { saveAccountSession } from "@/lib/auth-session";
import type { Group } from "@/types/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() })
}));

const authenticatedUser = {
  id: "user-aj",
  provider: "google",
  subject: "google-aj",
  email: "aj@example.com",
  username: "aj",
  display_name: "AJ"
};

const goaGroup: Group = {
  id: "group-goa",
  name: "Goa trip",
  role: "owner",
  members: [
    { id: "user-aj", username: "aj", display_name: "AJ", role: "owner" },
    { id: "user-sam", username: "sam", display_name: "Sam", role: "member" }
  ],
  bills: [
    {
      id: "bill-day-1",
      title: "Dinner day 1",
      status: "settling",
      created_at: "2026-07-26T00:00:00Z",
      grand_total_paise: 1200,
      pending_paise: 700,
      cleared_paise: 500,
      current_participant_id: "participant-aj",
      is_creator: true
    }
  ],
  total_paise: 1200,
  pending_paise: 700,
  cleared_paise: 500,
  created_at: "2026-07-25T00:00:00Z"
};

describe("persistent rooms dashboard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it("explains that accounts cover room creation and invite access", async () => {
    render(<DashboardPage />);

    expect(
      await screen.findByRole("heading", { name: /keep rooms, friends, and bills together/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/sign in to create rooms, join bill invites/i)).toBeInTheDocument();
    expect(screen.getByText(/google sign-in is not configured yet/i)).toBeInTheDocument();
  });

  it("renders friends, persistent rooms, multiple bills, and ledger totals for an account", async () => {
    saveAccountSession({ token: "google-id-token", user: authenticatedUser });
    vi.spyOn(api, "listGroups").mockResolvedValue({ groups: [goaGroup] });
    vi.spyOn(api, "listFriends").mockResolvedValue({
      friends: [{ id: "user-sam", username: "sam", display_name: "Sam" }]
    });

    render(<DashboardPage />);

    expect(await screen.findByRole("heading", { name: "Your rooms" })).toBeInTheDocument();
    expect(screen.getByText("@aj")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Friends" })).toBeInTheDocument();
    expect(screen.getByText("@sam")).toBeInTheDocument();

    const room = screen.getByRole("article");
    expect(within(room).getByRole("heading", { name: "Goa trip" })).toBeInTheDocument();
    expect(within(room).getByText("All bills")).toBeInTheDocument();
    expect(within(room).getByText("Pending")).toBeInTheDocument();
    expect(within(room).getByText("Cleared")).toBeInTheDocument();
    expect(within(room).getByText("₹5.00")).toBeInTheDocument();
    expect(within(room).getByText("Dinner day 1")).toBeInTheDocument();
    expect(within(room).getByRole("button", { name: "Add a bill" })).toBeInTheDocument();
  });

  it("adds friends by username and creates a room with selected friends", async () => {
    const user = userEvent.setup();
    saveAccountSession({ token: "google-id-token", user: authenticatedUser });
    vi.spyOn(api, "listGroups").mockResolvedValue({ groups: [] });
    vi.spyOn(api, "listFriends").mockResolvedValue({
      friends: [{ id: "user-sam", username: "sam", display_name: "Sam" }]
    });
    const addFriend = vi.spyOn(api, "addFriend").mockResolvedValue({
      id: "user-sam",
      username: "sam",
      display_name: "Sam"
    });
    const createGroup = vi.spyOn(api, "createGroup").mockResolvedValue(goaGroup);

    render(<DashboardPage />);
    await screen.findByRole("heading", { name: "Your rooms" });

    await user.type(screen.getByRole("textbox", { name: "Add by username" }), "SAM");
    await user.click(screen.getByRole("button", { name: "Add friend" }));
    expect(addFriend).toHaveBeenCalledWith("google-id-token", "sam");

    await user.type(screen.getByRole("textbox", { name: "Room name" }), "Goa trip");
    await user.click(screen.getByRole("checkbox", { name: "Sam" }));
    await user.click(screen.getByRole("button", { name: "Create room" }));
    expect(createGroup).toHaveBeenCalledWith("google-id-token", {
      name: "Goa trip",
      member_usernames: ["sam"]
    });
  });
});
