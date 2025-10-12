let native_port = browser.runtime.connectNative("slopspotter");

native_port.onDisconnect.addListener((response) => {
  if (response.error) {
    console.log(`Disconnected due to error: ${response.error.message}`);
  }
});

/*
Listen for messages from the app.
*/
native_port.onMessage.addListener((response) => {
  console.log(`Received: ${response}`);
});

/*
On a click on the browser action, send the app a message.
*/
browser.action.onClicked.addListener(() => {
  console.log("Sending:  ping");
  native_port.postMessage("ping");
});

/**
 * Communication with content script process
 */
browser.runtime.onConnect.addListener(function (port) {
  if (port.name === "slopspotter_background") {
    port.onMessage.addListener(function (message) {
      console.log("Message received from content script:", message);
      port.postMessage("test");
    });
  }
});
