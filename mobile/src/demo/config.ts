/**
 * Web demo switch.
 *
 * The demo build (EXPO_PUBLIC_DEMO=1) runs with no backend: API calls go to
 * src/demo/server.ts, which serves data recorded from the real pipeline.
 */
export const IS_DEMO = process.env.EXPO_PUBLIC_DEMO === "1";
