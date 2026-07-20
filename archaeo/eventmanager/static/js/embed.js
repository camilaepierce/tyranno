(function () {
    function notifyParentHeight() {
        if (window.parent === window) {
            return;
        }

        window.parent.postMessage(
            {
                type: "rex-embed-height",
                height: document.documentElement.scrollHeight,
            },
            "*",
        );
    }

    window.addEventListener("load", notifyParentHeight);
    window.addEventListener("resize", notifyParentHeight);

    if (typeof ResizeObserver !== "undefined") {
        var observer = new ResizeObserver(notifyParentHeight);
        observer.observe(document.body);
    }
})();
