import { shiNiangPlugin } from "./ShiNiangPlugin.js";

const plugins = window.shifuPlugins || [];
plugins.push(shiNiangPlugin);
window.shifuPlugins = plugins;

export { shiNiangPlugin };
