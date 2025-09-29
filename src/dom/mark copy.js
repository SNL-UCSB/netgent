((args) => {
  const {
    doHighlightElements,
    focusHighlightIndex,
    viewportExpansion,
    debugMode,
    showText = false, // <-- new flag
  } = args;
  let highlightIndex = 0; // Reset highlight index

  // Add caching mechanisms at the top level
  const DOM_CACHE = {
    boundingRects: new WeakMap(),
    clientRects: new WeakMap(),
    computedStyles: new WeakMap(),
    clearCache: () => {
      DOM_CACHE.boundingRects = new WeakMap();
      DOM_CACHE.clientRects = new WeakMap();
      DOM_CACHE.computedStyles = new WeakMap();
    },
  };

  function getCachedBoundingRect(element) {
    if (!element) return null;
    if (DOM_CACHE.boundingRects.has(element)) {
      return DOM_CACHE.boundingRects.get(element);
    }
    const rect = element.getBoundingClientRect();
    if (rect) {
      DOM_CACHE.boundingRects.set(element, rect);
    }
    return rect;
  }

  function getCachedComputedStyle(element) {
    if (!element) return null;
    if (DOM_CACHE.computedStyles.has(element)) {
      return DOM_CACHE.computedStyles.get(element);
    }
    const style = window.getComputedStyle(element);
    if (style) {
      DOM_CACHE.computedStyles.set(element, style);
    }
    return style;
  }

  function getCachedClientRects(element) {
    if (!element) return null;
    if (DOM_CACHE.clientRects.has(element)) {
      return DOM_CACHE.clientRects.get(element);
    }
    const rects = element.getClientRects();
    if (rects) {
      DOM_CACHE.clientRects.set(element, rects);
    }
    return rects;
  }

  const DOM_HASH_MAP = {};
  const ID = { current: 0 };
  const HIGHLIGHT_CONTAINER_ID = "playwright-highlight-container";
  const xpathCache = new WeakMap();

  function highlightElement(element, index, parentIframe = null) {
    if (!element) return index;
    const overlays = [];
    let label = null;
    let labelWidth = 20;
    let labelHeight = 16;
    let cleanupFn = null;
    try {
      let container = document.getElementById(HIGHLIGHT_CONTAINER_ID);
      if (!container) {
        container = document.createElement("div");
        container.id = HIGHLIGHT_CONTAINER_ID;
        container.style.position = "fixed";
        container.style.pointerEvents = "none";
        container.style.top = "0";
        container.style.left = "0";
        container.style.width = "100%";
        container.style.height = "100%";
        container.style.zIndex = "2147483647";
        container.style.backgroundColor = "transparent";
        document.body.appendChild(container);
      }
      const rects = element.getClientRects();
      if (!rects || rects.length === 0) return index;
      const colors = [
        "#FF0000",
        "#00FF00",
        "#0000FF",
        "#FFA500",
        "#800080",
        "#008080",
        "#FF69B4",
        "#4B0082",
        "#FF4500",
        "#2E8B57",
        "#DC143C",
        "#4682B4",
      ];
      const colorIndex = index % colors.length;
      const baseColor = colors[colorIndex];
      const backgroundColor = baseColor + "1A";
      let iframeOffset = { x: 0, y: 0 };
      if (parentIframe) {
        const iframeRect = parentIframe.getBoundingClientRect();
        iframeOffset.x = iframeRect.left;
        iframeOffset.y = iframeRect.top;
      }
      const fragment = document.createDocumentFragment();
      for (const rect of rects) {
        if (rect.width === 0 || rect.height === 0) continue;
        const overlay = document.createElement("div");
        overlay.style.position = "fixed";
        overlay.style.border = `2px solid ${baseColor}`;
        overlay.style.backgroundColor = backgroundColor;
        overlay.style.pointerEvents = "none";
        overlay.style.boxSizing = "border-box";
        const top = rect.top + iframeOffset.y;
        const left = rect.left + iframeOffset.x;
        overlay.style.top = `${top}px`;
        overlay.style.left = `${left}px`;
        overlay.style.width = `${rect.width}px`;
        overlay.style.height = `${rect.height}px`;
        fragment.appendChild(overlay);
        overlays.push({ element: overlay, initialRect: rect });
      }
      const firstRect = rects[0];
      label = document.createElement("div");
      label.className = "playwright-highlight-label";
      label.style.position = "fixed";
      label.style.background = baseColor;
      label.style.color = "white";
      label.style.padding = "1px 4px";
      label.style.borderRadius = "4px";
      label.style.fontSize = `${Math.min(
        12,
        Math.max(8, firstRect.height / 2)
      )}px`;
      label.textContent = index.toString();
      labelWidth = label.offsetWidth > 0 ? label.offsetWidth : labelWidth;
      labelHeight = label.offsetHeight > 0 ? label.offsetHeight : labelHeight;
      const firstRectTop = firstRect.top + iframeOffset.y;
      const firstRectLeft = firstRect.left + iframeOffset.x;
      let labelTop = firstRectTop + 2;
      let labelLeft = firstRectLeft + firstRect.width - labelWidth - 2;
      if (
        firstRect.width < labelWidth + 4 ||
        firstRect.height < labelHeight + 4
      ) {
        labelTop = firstRectTop - labelHeight - 2;
        labelLeft = firstRectLeft + firstRect.width - labelWidth;
        if (labelLeft < iframeOffset.x) labelLeft = firstRectLeft;
      }
      labelTop = Math.max(
        0,
        Math.min(labelTop, window.innerHeight - labelHeight)
      );
      labelLeft = Math.max(
        0,
        Math.min(labelLeft, window.innerWidth - labelWidth)
      );
      label.style.top = `${labelTop}px`;
      label.style.left = `${labelLeft}px`;
      fragment.appendChild(label);
      const updatePositions = () => {
        const newRects = element.getClientRects();
        let newIframeOffset = { x: 0, y: 0 };
        if (parentIframe) {
          const iframeRect = parentIframe.getBoundingClientRect();
          newIframeOffset.x = iframeRect.left;
          newIframeOffset.y = iframeRect.top;
        }
        overlays.forEach((overlayData, i) => {
          if (i < newRects.length) {
            const newRect = newRects[i];
            const newTop = newRect.top + newIframeOffset.y;
            const newLeft = newRect.left + newIframeOffset.x;
            overlayData.element.style.top = `${newTop}px`;
            overlayData.element.style.left = `${newLeft}px`;
            overlayData.element.style.width = `${newRect.width}px`;
            overlayData.element.style.height = `${newRect.height}px`;
            overlayData.element.style.display =
              newRect.width === 0 || newRect.height === 0 ? "none" : "block";
          } else {
            overlayData.element.style.display = "none";
          }
        });
        if (newRects.length < overlays.length) {
          for (let i = newRects.length; i < overlays.length; i++) {
            overlays[i].element.style.display = "none";
          }
        }
        if (label && newRects.length > 0) {
          const firstNewRect = newRects[0];
          const firstNewRectTop = firstNewRect.top + newIframeOffset.y;
          const firstNewRectLeft = firstNewRect.left + newIframeOffset.x;
          let newLabelTop = firstNewRectTop + 2;
          let newLabelLeft =
            firstNewRectLeft + firstNewRect.width - labelWidth - 2;
          if (
            firstNewRect.width < labelWidth + 4 ||
            firstNewRect.height < labelHeight + 4
          ) {
            newLabelTop = firstNewRectTop - labelHeight - 2;
            newLabelLeft = firstNewRectLeft + firstNewRect.width - labelWidth;
            if (newLabelLeft < newIframeOffset.x)
              newLabelLeft = firstNewRectLeft;
          }
          newLabelTop = Math.max(
            0,
            Math.min(newLabelTop, window.innerHeight - labelHeight)
          );
          newLabelLeft = Math.max(
            0,
            Math.min(newLabelLeft, window.innerWidth - labelWidth)
          );
          label.style.top = `${newLabelTop}px`;
          label.style.left = `${newLabelLeft}px`;
          label.style.display = "block";
        } else if (label) {
          label.style.display = "none";
        }
      };
      const throttleFunction = (func, delay) => {
        let lastCall = 0;
        return (...args) => {
          const now = performance.now();
          if (now - lastCall < delay) return;
          lastCall = now;
          return func(...args);
        };
      };
      const throttledUpdatePositions = throttleFunction(updatePositions, 16);
      window.addEventListener("scroll", throttledUpdatePositions, true);
      window.addEventListener("resize", throttledUpdatePositions);
      cleanupFn = () => {
        window.removeEventListener("scroll", throttledUpdatePositions, true);
        window.removeEventListener("resize", throttledUpdatePositions);
        overlays.forEach((overlay) => overlay.element.remove());
        if (label) label.remove();
      };
      container.appendChild(fragment);
      return index + 1;
    } finally {
      if (cleanupFn) {
        (window._highlightCleanupFunctions =
          window._highlightCleanupFunctions || []).push(cleanupFn);
      }
    }
  }

  function getElementPosition(currentElement) {
    if (!currentElement.parentElement) {
      return 0;
    }
    const tagName = currentElement.nodeName.toLowerCase();
    const siblings = Array.from(currentElement.parentElement.children).filter(
      (sib) => sib.nodeName.toLowerCase() === tagName
    );
    if (siblings.length === 1) {
      return 0;
    }
    const index = siblings.indexOf(currentElement) + 1;
    return index;
  }

  function getXPathTree(element, stopAtBoundary = true) {
    if (xpathCache.has(element)) return xpathCache.get(element);
    const segments = [];
    let currentElement = element;
    while (currentElement && currentElement.nodeType === Node.ELEMENT_NODE) {
      if (
        stopAtBoundary &&
        (currentElement.parentNode instanceof ShadowRoot ||
          currentElement.parentNode instanceof HTMLIFrameElement)
      ) {
        break;
      }
      const position = getElementPosition(currentElement);
      const tagName = currentElement.nodeName.toLowerCase();
      const xpathIndex = position > 0 ? `[${position}]` : "";
      segments.unshift(`${tagName}${xpathIndex}`);
      currentElement = currentElement.parentNode;
    }
    const result = segments.join("/");
    xpathCache.set(element, result);
    return result;
  }

  function isTextNodeVisible(textNode) {
    try {
      if (viewportExpansion === -1) {
        const parentElement = textNode.parentElement;
        if (!parentElement) return false;
        try {
          return parentElement.checkVisibility({
            checkOpacity: true,
            checkVisibilityCSS: true,
          });
        } catch (e) {
          const style = window.getComputedStyle(parentElement);
          return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            style.opacity !== "0"
          );
        }
      }
      const range = document.createRange();
      range.selectNodeContents(textNode);
      const rects = range.getClientRects();
      if (!rects || rects.length === 0) {
        return false;
      }
      let isAnyRectVisible = false;
      let isAnyRectInViewport = false;
      for (const rect of rects) {
        if (rect.width > 0 && rect.height > 0) {
          isAnyRectVisible = true;
          if (
            !(
              rect.bottom < -viewportExpansion ||
              rect.top > window.innerHeight + viewportExpansion ||
              rect.right < -viewportExpansion ||
              rect.left > window.innerWidth + viewportExpansion
            )
          ) {
            isAnyRectInViewport = true;
            break;
          }
        }
      }
      if (!isAnyRectVisible || !isAnyRectInViewport) {
        return false;
      }
      const parentElement = textNode.parentElement;
      if (!parentElement) return false;
      try {
        return parentElement.checkVisibility({
          checkOpacity: true,
          checkVisibilityCSS: true,
        });
      } catch (e) {
        const style = window.getComputedStyle(parentElement);
        return (
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          style.opacity !== "0"
        );
      }
    } catch (e) {
      console.warn("Error checking text node visibility:", e);
      return false;
    }
  }

  function isElementAccepted(element) {
    if (!element || !element.tagName) return false;
    const alwaysAccept = new Set([
      "body",
      "div",
      "main",
      "article",
      "section",
      "nav",
      "header",
      "footer",
    ]);
    const tagName = element.tagName.toLowerCase();
    if (alwaysAccept.has(tagName)) return true;
    const leafElementDenyList = new Set([
      "svg",
      "script",
      "style",
      "link",
      "meta",
      "noscript",
      "template",
    ]);
    return !leafElementDenyList.has(tagName);
  }

  function isElementVisible(element) {
    const style = getCachedComputedStyle(element);
    return (
      element.offsetWidth > 0 &&
      element.offsetHeight > 0 &&
      style?.visibility !== "hidden" &&
      style?.display !== "none"
    );
  }

  function isInteractiveElement(element) {
    if (!element || element.nodeType !== Node.ELEMENT_NODE) {
      return false;
    }
    const tagName = element.tagName.toLowerCase();
    const style = getCachedComputedStyle(element);
    const interactiveCursors = new Set([
      "pointer",
      "move",
      "text",
      "grab",
      "grabbing",
      "cell",
      "copy",
      "alias",
      "all-scroll",
      "col-resize",
      "context-menu",
      "crosshair",
      "e-resize",
      "ew-resize",
      "help",
      "n-resize",
      "ne-resize",
      "nesw-resize",
      "ns-resize",
      "nw-resize",
      "nwse-resize",
      "row-resize",
      "s-resize",
      "se-resize",
      "sw-resize",
      "vertical-text",
      "w-resize",
      "zoom-in",
      "zoom-out",
    ]);
    const nonInteractiveCursors = new Set([
      "not-allowed",
      "no-drop",
      "wait",
      "progress",
      "initial",
      "inherit",
    ]);
    function doesElementHaveInteractivePointer(element) {
      if (element.tagName.toLowerCase() === "html") return false;
      if (style?.cursor && interactiveCursors.has(style.cursor)) return true;
      return false;
    }
    let isInteractiveCursor = doesElementHaveInteractivePointer(element);
    if (isInteractiveCursor) {
      return true;
    }
    const interactiveElements = new Set([
      "a",
      "button",
      "input",
      "select",
      "textarea",
      "details",
      "summary",
      "label",
      "option",
      "optgroup",
      "fieldset",
      "legend",
    ]);
    const explicitDisableTags = new Set(["disabled", "readonly"]);
    if (interactiveElements.has(tagName)) {
      if (style?.cursor && nonInteractiveCursors.has(style.cursor)) {
        return false;
      }
      for (const disableTag of explicitDisableTags) {
        if (
          element.hasAttribute(disableTag) ||
          element.getAttribute(disableTag) === "true" ||
          element.getAttribute(disableTag) === ""
        ) {
          return false;
        }
      }
      if (element.disabled) {
        return false;
      }
      if (element.readOnly) {
        return false;
      }
      if (element.inert) {
        return false;
      }
      return true;
    }
    const role = element.getAttribute("role");
    const ariaRole = element.getAttribute("aria-role");
    if (
      element.getAttribute("contenteditable") === "true" ||
      element.isContentEditable
    ) {
      return true;
    }
    if (
      element.classList &&
      (element.classList.contains("button") ||
        element.classList.contains("dropdown-toggle") ||
        element.getAttribute("data-index") ||
        element.getAttribute("data-toggle") === "dropdown" ||
        element.getAttribute("aria-haspopup") === "true")
    ) {
      return true;
    }
    const interactiveRoles = new Set([
      "button",
      "menu",
      "menubar",
      "menuitem",
      "menuitemradio",
      "menuitemcheckbox",
      "radio",
      "checkbox",
      "tab",
      "switch",
      "slider",
      "spinbutton",
      "combobox",
      "searchbox",
      "textbox",
      "listbox",
      "option",
      "scrollbar",
    ]);
    const hasInteractiveRole =
      interactiveElements.has(tagName) ||
      (role && interactiveRoles.has(role)) ||
      (ariaRole && interactiveRoles.has(ariaRole));
    if (hasInteractiveRole) return true;
    try {
      if (typeof getEventListeners === "function") {
        const listeners = getEventListeners(element);
        const mouseEvents = ["click", "mousedown", "mouseup", "dblclick"];
        for (const eventType of mouseEvents) {
          if (listeners[eventType] && listeners[eventType].length > 0) {
            return true;
          }
        }
      }
      const getEventListenersForNode =
        element?.ownerDocument?.defaultView?.getEventListenersForNode ||
        window.getEventListenersForNode;
      if (typeof getEventListenersForNode === "function") {
        const listeners = getEventListenersForNode(element);
        const interactionEvents = [
          "click",
          "mousedown",
          "mouseup",
          "keydown",
          "keyup",
          "submit",
          "change",
          "input",
          "focus",
          "blur",
        ];
        for (const eventType of interactionEvents) {
          for (const listener of listeners) {
            if (listener.type === eventType) {
              return true;
            }
          }
        }
      }
      const commonMouseAttrs = [
        "onclick",
        "onmousedown",
        "onmouseup",
        "ondblclick",
      ];
      for (const attr of commonMouseAttrs) {
        if (element.hasAttribute(attr) || typeof element[attr] === "function") {
          return true;
        }
      }
    } catch (e) {}
    return false;
  }

  function isTopElement(element) {
    if (viewportExpansion === -1) {
      return true;
    }
    const rects = getCachedClientRects(element);
    if (!rects || rects.length === 0) {
      return false;
    }
    let isAnyRectInViewport = false;
    for (const rect of rects) {
      if (
        rect.width > 0 &&
        rect.height > 0 &&
        !(
          rect.bottom < -viewportExpansion ||
          rect.top > window.innerHeight + viewportExpansion ||
          rect.right < -viewportExpansion ||
          rect.left > window.innerWidth + viewportExpansion
        )
      ) {
        isAnyRectInViewport = true;
        break;
      }
    }
    if (!isAnyRectInViewport) {
      return false;
    }
    let doc = element.ownerDocument;
    if (doc !== window.document) {
      return true;
    }
    const shadowRoot = element.getRootNode();
    if (shadowRoot instanceof ShadowRoot) {
      const centerX =
        rects[Math.floor(rects.length / 2)].left +
        rects[Math.floor(rects.length / 2)].width / 2;
      const centerY =
        rects[Math.floor(rects.length / 2)].top +
        rects[Math.floor(rects.length / 2)].height / 2;
      try {
        const topEl = shadowRoot.elementFromPoint(centerX, centerY);
        if (!topEl) return false;
        let current = topEl;
        while (current && current !== shadowRoot) {
          if (current === element) return true;
          current = current.parentElement;
        }
        return false;
      } catch (e) {
        return true;
      }
    }
    const margin = 5;
    const rect = rects[Math.floor(rects.length / 2)];
    const checkPoints = [
      { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 },
      { x: rect.left + margin, y: rect.top + margin },
      { x: rect.right - margin, y: rect.bottom - margin },
    ];
    return checkPoints.some(({ x, y }) => {
      try {
        const topEl = document.elementFromPoint(x, y);
        if (!topEl) return false;
        let current = topEl;
        while (current && current !== document.documentElement) {
          if (current === element) return true;
          current = current.parentElement;
        }
        return false;
      } catch (e) {
        return true;
      }
    });
  }

  function isInExpandedViewport(element, viewportExpansion) {
    if (viewportExpansion === -1) {
      return true;
    }
    const rects = element.getClientRects();
    if (!rects || rects.length === 0) {
      const boundingRect = getCachedBoundingRect(element);
      if (
        !boundingRect ||
        boundingRect.width === 0 ||
        boundingRect.height === 0
      ) {
        return false;
      }
      return !(
        boundingRect.bottom < -viewportExpansion ||
        boundingRect.top > window.innerHeight + viewportExpansion ||
        boundingRect.right < -viewportExpansion ||
        boundingRect.left > window.innerWidth + viewportExpansion
      );
    }
    for (const rect of rects) {
      if (rect.width === 0 || rect.height === 0) continue;
      if (
        !(
          rect.bottom < -viewportExpansion ||
          rect.top > window.innerHeight + viewportExpansion ||
          rect.right < -viewportExpansion ||
          rect.left > window.innerWidth + viewportExpansion
        )
      ) {
        return true;
      }
    }
    return false;
  }

  function isInteractiveCandidate(element) {
    if (!element || element.nodeType !== Node.ELEMENT_NODE) return false;
    const tagName = element.tagName.toLowerCase();
    const interactiveElements = new Set([
      "a",
      "button",
      "input",
      "select",
      "textarea",
      "details",
      "summary",
      "label",
    ]);
    if (interactiveElements.has(tagName)) return true;
    const hasQuickInteractiveAttr =
      element.hasAttribute("onclick") ||
      element.hasAttribute("role") ||
      element.hasAttribute("tabindex") ||
      element.hasAttribute("aria-") ||
      element.hasAttribute("data-action") ||
      element.getAttribute("contenteditable") === "true";
    return hasQuickInteractiveAttr;
  }

  const DISTINCT_INTERACTIVE_TAGS = new Set([
    "a",
    "button",
    "input",
    "select",
    "textarea",
    "summary",
    "details",
    "label",
    "option",
  ]);
  const INTERACTIVE_ROLES = new Set([
    "button",
    "link",
    "menuitem",
    "menuitemradio",
    "menuitemcheckbox",
    "radio",
    "checkbox",
    "tab",
    "switch",
    "slider",
    "spinbutton",
    "combobox",
    "searchbox",
    "textbox",
    "listbox",
    "option",
    "scrollbar",
  ]);

  function isHeuristicallyInteractive(element) {
    if (!element || element.nodeType !== Node.ELEMENT_NODE) return false;
    if (!isElementVisible(element)) return false;
    const hasInteractiveAttributes =
      element.hasAttribute("role") ||
      element.hasAttribute("tabindex") ||
      element.hasAttribute("onclick") ||
      typeof element.onclick === "function";
    const hasInteractiveClass =
      /\b(btn|clickable|menu|item|entry|link)\b/i.test(element.className || "");
    const isInKnownContainer = Boolean(
      element.closest('button,a,[role="button"],.menu,.dropdown,.list,.toolbar')
    );
    const hasVisibleChildren = [...element.children].some(isElementVisible);
    const isParentBody =
      element.parentElement && element.parentElement.isSameNode(document.body);
    return (
      (isInteractiveElement(element) ||
        hasInteractiveAttributes ||
        hasInteractiveClass) &&
      hasVisibleChildren &&
      isInKnownContainer &&
      !isParentBody
    );
  }

  function isElementDistinctInteraction(element) {
    if (!element || element.nodeType !== Node.ELEMENT_NODE) {
      return false;
    }
    const tagName = element.tagName.toLowerCase();
    const role = element.getAttribute("role");
    if (tagName === "iframe") {
      return true;
    }
    if (DISTINCT_INTERACTIVE_TAGS.has(tagName)) {
      return true;
    }
    if (role && INTERACTIVE_ROLES.has(role)) {
      return true;
    }
    if (
      element.isContentEditable ||
      element.getAttribute("contenteditable") === "true"
    ) {
      return true;
    }
    if (
      element.hasAttribute("data-testid") ||
      element.hasAttribute("data-cy") ||
      element.hasAttribute("data-test")
    ) {
      return true;
    }
    if (
      element.hasAttribute("onclick") ||
      typeof element.onclick === "function"
    ) {
      return true;
    }
    try {
      const getEventListenersForNode =
        element?.ownerDocument?.defaultView?.getEventListenersForNode ||
        window.getEventListenersForNode;
      if (typeof getEventListenersForNode === "function") {
        const listeners = getEventListenersForNode(element);
        const interactionEvents = [
          "click",
          "mousedown",
          "mouseup",
          "keydown",
          "keyup",
          "submit",
          "change",
          "input",
          "focus",
          "blur",
        ];
        for (const eventType of interactionEvents) {
          for (const listener of listeners) {
            if (listener.type === eventType) {
              return true;
            }
          }
        }
      }
      const commonEventAttrs = [
        "onmousedown",
        "onmouseup",
        "onkeydown",
        "onkeyup",
        "onsubmit",
        "onchange",
        "oninput",
        "onfocus",
        "onblur",
      ];
      if (commonEventAttrs.some((attr) => element.hasAttribute(attr))) {
        return true;
      }
    } catch (e) {}
    if (isHeuristicallyInteractive(element)) {
      return true;
    }
    return false;
  }

  function handleHighlighting(
    nodeData,
    node,
    parentIframe,
    isParentHighlighted
  ) {
    if (!nodeData.isInteractive) return false;
    let shouldHighlight = false;
    if (!isParentHighlighted) {
      shouldHighlight = true;
    } else {
      if (isElementDistinctInteraction(node)) {
        shouldHighlight = true;
      } else {
        shouldHighlight = false;
      }
    }
    if (shouldHighlight) {
      nodeData.isInViewport = isInExpandedViewport(node, viewportExpansion);
      if (nodeData.isInViewport || viewportExpansion === -1) {
        nodeData.highlightIndex = highlightIndex++;
        if (doHighlightElements) {
          if (focusHighlightIndex >= 0) {
            if (focusHighlightIndex === nodeData.highlightIndex) {
              highlightElement(node, nodeData.highlightIndex, parentIframe);
            }
          } else {
            highlightElement(node, nodeData.highlightIndex, parentIframe);
          }
          return true;
        }
      }
    }
    return false;
  }

  function buildDomTree(
    node,
    parentIframe = null,
    isParentHighlighted = false
  ) {
    if (
      !node ||
      node.id === HIGHLIGHT_CONTAINER_ID ||
      (node.nodeType !== Node.ELEMENT_NODE && node.nodeType !== Node.TEXT_NODE)
    ) {
      return null;
    }
    if (!node || node.id === HIGHLIGHT_CONTAINER_ID) {
      return null;
    }
    if (node === document.body) {
      const nodeData = {
        tagName: "body",
        attributes: {},
        xpath: "/body",
        children: [],
      };
      for (const child of node.childNodes) {
        const domElement = buildDomTree(child, parentIframe, false);
        if (domElement) nodeData.children.push(domElement);
      }
      const id = ID.current++;
      DOM_HASH_MAP[id] = nodeData;
      return id;
    }
    if (
      node.nodeType !== Node.ELEMENT_NODE &&
      node.nodeType !== Node.TEXT_NODE
    ) {
      return null;
    }
    if (node.nodeType === Node.TEXT_NODE) {
      const textContent = node.textContent?.trim();
      if (!textContent) {
        return null;
      }
      const parentElement = node.parentElement;
      if (!parentElement || parentElement.tagName.toLowerCase() === "script") {
        return null;
      }
      const id = ID.current++;
      DOM_HASH_MAP[id] = {
        type: "TEXT_NODE",
        text: textContent,
        isVisible: isTextNodeVisible(node),
      };
      return id;
    }
    if (node.nodeType === Node.ELEMENT_NODE && !isElementAccepted(node)) {
      return null;
    }
    if (viewportExpansion !== -1 && !node.shadowRoot) {
      const rect = getCachedBoundingRect(node);
      const style = getCachedComputedStyle(node);
      const isFixedOrSticky =
        style && (style.position === "fixed" || style.position === "sticky");
      const hasSize = node.offsetWidth > 0 || node.offsetHeight > 0;
      if (
        !rect ||
        (!isFixedOrSticky &&
          !hasSize &&
          (rect.bottom < -viewportExpansion ||
            rect.top > window.innerHeight + viewportExpansion ||
            rect.right < -viewportExpansion ||
            rect.left > window.innerWidth + viewportExpansion))
      ) {
        return null;
      }
    }
    const nodeData = {
      tagName: node.tagName.toLowerCase(),
      attributes: {},
      xpath: getXPathTree(node, true),
      children: [],
    };
    if (
      isInteractiveCandidate(node) ||
      node.tagName.toLowerCase() === "iframe" ||
      node.tagName.toLowerCase() === "body"
    ) {
      const attributeNames = node.getAttributeNames?.() || [];
      for (const name of attributeNames) {
        const value = node.getAttribute(name);
        nodeData.attributes[name] = value;
      }
    }
    let nodeWasHighlighted = false;
    if (node.nodeType === Node.ELEMENT_NODE) {
      nodeData.isVisible = isElementVisible(node);
      if (nodeData.isVisible) {
        nodeData.isTopElement = isTopElement(node);

        // detect headers when showText is on
        const tagName = node.tagName.toLowerCase();
        const isHeader = showText && /^h[1-6]$/.test(tagName);

        const role = node.getAttribute("role");
        const isMenuContainer =
          role === "menu" || role === "menubar" || role === "listbox";

        // only enter the "highlight" path if either:
        //  • it's truly interactive, or
        //  • it's a header and showText=true
        if (nodeData.isTopElement || isMenuContainer || isHeader) {
          nodeData.isInteractive = isInteractiveElement(node) || isHeader;
          nodeWasHighlighted = handleHighlighting(
            nodeData,
            node,
            parentIframe,
            isParentHighlighted
          );
        }
      }
    }
    if (node.tagName) {
      const tagName = node.tagName.toLowerCase();
      if (tagName === "iframe") {
        try {
          const iframeDoc =
            node.contentDocument || node.contentWindow?.document;
          if (iframeDoc) {
            for (const child of iframeDoc.childNodes) {
              const domElement = buildDomTree(child, node, false);
              if (domElement) nodeData.children.push(domElement);
            }
          }
        } catch (e) {
          console.warn("Unable to access iframe:", e);
        }
      } else if (
        node.isContentEditable ||
        node.getAttribute("contenteditable") === "true" ||
        node.id === "tinymce" ||
        node.classList.contains("mce-content-body") ||
        (tagName === "body" && node.getAttribute("data-id")?.startsWith("mce_"))
      ) {
        for (const child of node.childNodes) {
          const domElement = buildDomTree(
            child,
            parentIframe,
            nodeWasHighlighted
          );
          if (domElement) nodeData.children.push(domElement);
        }
      } else {
        if (node.shadowRoot) {
          nodeData.shadowRoot = true;
          for (const child of node.shadowRoot.childNodes) {
            const domElement = buildDomTree(
              child,
              parentIframe,
              nodeWasHighlighted
            );
            if (domElement) nodeData.children.push(domElement);
          }
        }
        for (const child of node.childNodes) {
          const passHighlightStatusToChild =
            nodeWasHighlighted || isParentHighlighted;
          const domElement = buildDomTree(
            child,
            parentIframe,
            passHighlightStatusToChild
          );
          if (domElement) nodeData.children.push(domElement);
        }
      }
    }
    // Skip empty anchor tags only if they have no dimensions and no children
    if (
      nodeData.tagName === "a" &&
      nodeData.children.length === 0 &&
      !nodeData.attributes.href
    ) {
      const rect = getCachedBoundingRect(node);
      const hasSize =
        (rect && rect.width > 0 && rect.height > 0) ||
        node.offsetWidth > 0 ||
        node.offsetHeight > 0;
      if (!hasSize) {
        return null;
      }
    }
    const id = ID.current++;
    DOM_HASH_MAP[id] = nodeData;
    return id;
  }

  const rootId = buildDomTree(document.body);

  // Clear the cache before starting
  DOM_CACHE.clearCache();

  return { rootId, map: DOM_HASH_MAP };
})({
  doHighlightElements: true,
  focusHighlightIndex: -1,
  viewportExpansion: 0,
  debugMode: false,
  showText: true, // or false
});
