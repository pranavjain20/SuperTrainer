module.exports = {
  extends: ["expo", "prettier"],
  plugins: ["prettier"],
  rules: {
    "prettier/prettier": "warn",
    // Allow default exports (Expo Router requires them for screens)
    "import/no-default-export": "off",
  },
};
