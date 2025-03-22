/*jslint es6*/
/*global
    __dirname */

module.exports = {
    entry: "./main.js",
    devtool: "inline-source-map",
    output: {
        path: __dirname + "../../dist/",
        publicPath: "/",
        filename: "main.js"
    },
    devServer: {
        contentBase: "../dist"
    },
    resolve: {
        fallback: {
            fs: false
        }
    }
};
