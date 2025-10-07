/*
On startup, connect to the "ping_pong" app.
*/
let port = browser.runtime.connectNative("slopspotter");

/*
Listen for messages from the app.
*/
port.onMessage.addListener((response) => {
  console.log(`Received: ${response}`);
});

/*
On a click on the browser action, send the app a message.
*/
browser.action.onClicked.addListener(() => {
  console.log("Sending:  ping");
  port.postMessage("ping");
});
