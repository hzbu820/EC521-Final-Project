function logCheckboxStatus(event) {
  if (event.target.checked) {
    console.debug("Checkbox is checked");
  } else {
    console.debug("Checkbox is not checked");
  }
}

document
  .getElementById("enable_checkbox")
  .addEventListener("click", logCheckboxStatus);

const background_port = browser.runtime.connect({
  name: "slopspotter_background",
});

background_port.postMessage("test");
background_port.onMessage.addListener(function (msg) {
  console.log("Message from background via port:", msg);
});
