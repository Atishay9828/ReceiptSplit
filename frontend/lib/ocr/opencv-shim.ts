// PaddleOCR.js imports OpenCV for its main-thread pipeline. ReceiptSplit uses
// the SDK's worker pipeline, where the worker owns its bundled OpenCV runtime.
// Keeping this browser/server shim avoids pulling the Node-aware OpenCV bundle
// into Next's page graph. If worker mode is ever removed, delete this shim and
// import the package's OpenCV runtime intentionally.
const opencvShim = {};

export default opencvShim;
