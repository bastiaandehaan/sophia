// playwright.config.js
module.exports = {
  timeout: 60000,
  expect: {
    timeout: 15000
  },
  retries: 2,
  use: {
    headless: false,
    actionTimeout: 30000,
    navigationTimeout: 60000,
    viewport: { width: 1280, height: 720 }
  }
};