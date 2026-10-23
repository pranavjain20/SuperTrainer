import suggestions from "@/src/constants/brainSuggestions.json";

import fixture from "../fixture.json";

it("has a recorded Brain answer for every suggested question", () => {
  expect(fixture.brain.map((b) => b.question)).toEqual(suggestions);
});
