(function () {
  // Helper function to get XPath for an element
  function getXPathTree(element, stopAtBoundary = true) {
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
    return segments.join("/");
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

  // Helper function to get CSS selector
  function getCssSelector(element) {
    if (!element || element.nodeType !== Node.ELEMENT_NODE) return "";

    const path = [];
    while (element && element.nodeType === Node.ELEMENT_NODE) {
      let selector = element.nodeName.toLowerCase();

      if (element.id) {
        selector += "#" + element.id;
        path.unshift(selector);
        break;
      } else {
        let sib = element;
        let nth = 1;
        while ((sib = sib.previousElementSibling)) {
          if (sib.nodeName.toLowerCase() === selector) nth++;
        }
        if (nth !== 1) selector += `:nth-of-type(${nth})`;
      }

      path.unshift(selector);
      element = element.parentElement;
    }

    return path.join(" > ");
  }

  // Safe attributes for enhanced CSS selector
  const SAFE_ATTRIBUTES = new Set([
    "id",
    "name",
    "type",
    "placeholder",
    "aria-label",
    "aria-labelledby",
    "aria-describedby",
    "role",
    "for",
    "autocomplete",
    "required",
    "readonly",
    "alt",
    "title",
    "src",
    "href",
    "target",
    "data-id",
    "data-qa",
    "data-cy",
    "data-testid",
  ]);

  // Helper function to get enhanced CSS selector
  function getEnhancedCSSSelector(element, xpath) {
    try {
      if (!element || element.nodeType !== Node.ELEMENT_NODE) return "";

      let selector = element.tagName.toLowerCase();

      // Add valid classes
      if (element.classList && element.classList.length > 0) {
        element.classList.forEach((className) => {
          if (/^[a-zA-Z_][a-zA-Z0-9_-]*$/.test(className)) {
            try {
              selector += `.${CSS.escape(className)}`;
            } catch (err) {
              // Fallback if CSS.escape is not available
              selector += `.${className.replace(/[^a-zA-Z0-9_-]/g, "")}`;
            }
          }
        });
      }

      // Add safe attributes
      if (element.attributes) {
        for (const attr of Array.from(element.attributes)) {
          const name = attr.name;
          const value = attr.value;
          if (name === "class" || !SAFE_ATTRIBUTES.has(name)) continue;

          try {
            const safeName = CSS.escape
              ? CSS.escape(name)
              : name.replace(/[^a-zA-Z0-9_-]/g, "");
            const safeValue = value.replace(/"/g, '\\"');
            if (/["'<>\s]/.test(value)) {
              selector += `[${safeName}*="${safeValue}"]`;
            } else {
              selector += `[${safeName}="${safeValue}"]`;
            }
          } catch (err) {
            // Skip attribute if there's an error
            continue;
          }
        }
      }

      return selector;
    } catch (err) {
      console.error("Error generating enhanced selector:", err);
      return `${element.tagName.toLowerCase()}[xpath="${xpath.replace(
        /"/g,
        "'"
      )}"]`;
    }
  }

  // Helper function to get accessible name
  function getAccessibleName(element) {
    if (!element) return "";

    // Check aria-label
    if (element.hasAttribute("aria-label")) {
      return element.getAttribute("aria-label").trim();
    }

    // Check aria-labelledby
    if (element.hasAttribute("aria-labelledby")) {
      const labelIds = element.getAttribute("aria-labelledby").split(/\s+/);
      const labels = labelIds
        .map((id) => {
          const labelElement = document.getElementById(id);
          return labelElement ? labelElement.textContent.trim() : "";
        })
        .filter((text) => text);
      if (labels.length > 0) return labels.join(" ");
    }

    // Check associated label
    if (element.id) {
      const label = document.querySelector(`label[for="${element.id}"]`);
      if (label) return label.textContent.trim();
    }

    // Check parent label
    const parentLabel = element.closest("label");
    if (parentLabel) return parentLabel.textContent.trim();

    // Check title attribute
    if (element.hasAttribute("title")) {
      return element.getAttribute("title").trim();
    }

    // Check alt attribute for images
    if (
      element.tagName.toLowerCase() === "img" &&
      element.hasAttribute("alt")
    ) {
      return element.getAttribute("alt").trim();
    }

    // Check placeholder for inputs
    if (element.hasAttribute("placeholder")) {
      return element.getAttribute("placeholder").trim();
    }

    // For buttons, use text content
    if (element.tagName.toLowerCase() === "button") {
      return element.textContent.trim();
    }

    return "";
  }

  function showVisibleElements() {
    // Get all elements in the DOM
    const allElements = document.querySelectorAll("*");
    const candidateElements = [];

    // First pass: collect all visible elements with text
    allElements.forEach((element) => {
      // Get computed styles for the element
      const styles = window.getComputedStyle(element);

      // Check if element is visible (basic visibility)
      const isVisible =
        styles.display !== "none" &&
        styles.visibility !== "hidden" &&
        styles.opacity !== "0" &&
        element.offsetWidth > 0 &&
        element.offsetHeight > 0;

      if (isVisible) {
        // Check if element has direct text content
        const hasDirectText =
          element.childNodes &&
          Array.from(element.childNodes).some(
            (node) =>
              node.nodeType === Node.TEXT_NODE &&
              node.textContent.trim().length > 0
          );

        if (hasDirectText) {
          // Check if element is in viewport
          const rect = element.getBoundingClientRect();
          const isInViewport =
            rect.top < window.innerHeight &&
            rect.bottom > 0 &&
            rect.left < window.innerWidth &&
            rect.right > 0;

          if (isInViewport) {
            // Get z-index and stacking context information
            const zIndex =
              styles.zIndex === "auto" ? 0 : parseInt(styles.zIndex) || 0;
            const position = styles.position;

            // Get only the direct text content
            const directText = Array.from(element.childNodes)
              .filter((node) => node.nodeType === Node.TEXT_NODE)
              .map((node) => node.textContent.trim())
              .join(" ")
              .trim();

            // Generate metadata
            const xpath = getXPathTree(element, true);
            const cssSelector = getCssSelector(element);
            const enhancedCssSelector = getEnhancedCSSSelector(element, xpath);
            const tagName = element.tagName.toLowerCase();
            const ariaRole = element.getAttribute("role") || tagName;
            const accessibleName = getAccessibleName(element);

            candidateElements.push({
              element: element,
              tagName: element.tagName.toLowerCase(),
              id: element.id || null,
              classes: element.className || null,
              text:
                directText.substring(0, 100) +
                (directText.length > 100 ? "..." : ""),
              zIndex: zIndex,
              position: position,
              rect: rect,
              styles: styles,
              // Add all metadata fields from build_dom.js
              cssSelector,
              enhancedCssSelector,
              xpath,
              ariaRole,
              accessibleName,
            });
          }
        }
      }
    });

    if (candidateElements.length === 0) {
      return [];
    }

    // Find elements on the topmost layer by checking what's actually visible
    const layerElements = [];

    candidateElements.forEach((candidate) => {
      const rect = candidate.rect;

      // Test center point to see what's actually on top
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const topElement = document.elementFromPoint(centerX, centerY);

      // Check if this element or its descendants are on the topmost layer
      if (
        candidate.element === topElement ||
        candidate.element.contains(topElement)
      ) {
        // This element is visible at its center point
        layerElements.push({
          element: candidate.element,
          tagName: candidate.tagName,
          id: candidate.id,
          classes: candidate.classes,
          text: candidate.text,
          zIndex: candidate.zIndex,
          position: candidate.position,
          coordinates: {
            top: candidate.element.offsetTop,
            left: candidate.element.offsetLeft,
            width: candidate.element.offsetWidth,
            height: candidate.element.offsetHeight,
          },
          viewport: {
            top: Math.round(rect.top),
            left: Math.round(rect.left),
            bottom: Math.round(rect.bottom),
            right: Math.round(rect.right),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          },
          // Add all metadata fields from build_dom.js
          cssSelector: candidate.cssSelector,
          enhancedCssSelector: candidate.enhancedCssSelector,
          xpath: candidate.xpath,
          ariaRole: candidate.ariaRole,
          accessibleName: candidate.accessibleName,
        });
      }
    });

    // If we found elements on the top layer, return only those
    if (layerElements.length > 0) {
      return layerElements;
    }

    // Fallback: find highest z-index and return only elements at that level
    const maxZIndex = Math.max(...candidateElements.map((el) => el.zIndex));
    return candidateElements
      .filter((el) => el.zIndex === maxZIndex)
      .map((candidate) => ({
        element: candidate.element,
        tagName: candidate.tagName,
        id: candidate.id,
        classes: candidate.classes,
        text: candidate.text,
        zIndex: candidate.zIndex,
        position: candidate.position,
        coordinates: {
          top: candidate.element.offsetTop,
          left: candidate.element.offsetLeft,
          width: candidate.element.offsetWidth,
          height: candidate.element.offsetHeight,
        },
        viewport: {
          top: Math.round(candidate.rect.top),
          left: Math.round(candidate.rect.left),
          bottom: Math.round(candidate.rect.bottom),
          right: Math.round(candidate.rect.right),
          width: Math.round(candidate.rect.width),
          height: Math.round(candidate.rect.height),
        },
        // Add all metadata fields from build_dom.js
        cssSelector: candidate.cssSelector,
        enhancedCssSelector: candidate.enhancedCssSelector,
        xpath: candidate.xpath,
        ariaRole: candidate.ariaRole,
        accessibleName: candidate.accessibleName,
      }));
  }

  // Alternative function that highlights visible elements on the page
  function highlightVisibleElements() {
    const visibleElements = showVisibleElements();

    // Add temporary highlighting
    // visibleElements.forEach((item, index) => {
    //   const element = item.element;
    //   const originalBorder = element.style.border;
    //   const originalBoxShadow = element.style.boxShadow;

    //   // Add highlight styling
    //   element.style.border = "2px solid red";
    //   element.style.boxShadow = "0 0 5px rgba(255, 0, 0, 0.5)";

    //   // Remove highlighting after 250ms
    //   setTimeout(() => {
    //     element.style.border = originalBorder;
    //     element.style.boxShadow = originalBoxShadow;
    //   }, 250);
    // });

    // Return only serializable data, removing complex objects
    return visibleElements.map((item) => ({
      tagName: item.tagName,
      id: item.id,
      text: item.text,
      cssSelector: item.cssSelector,
      enhancedCssSelector: item.enhancedCssSelector,
      xpath: item.xpath,
      ariaRole: item.ariaRole,
      accessibleName: item.accessibleName,
    }));
  }

  // Function to get the topmost element (only from the top layer)
  function getTopmostElement() {
    const visibleElements = showVisibleElements();

    if (visibleElements.length === 0) {
      return null;
    }

    // Sort by viewport position since all elements are already on the top layer
    const sortedElements = visibleElements.sort(
      (a, b) => a.viewport.top - b.viewport.top
    );

    return sortedElements[0];
  }

  // Function to get the current top layer z-index
  function getCurrentTopLayer() {
    const allElements = document.querySelectorAll("*");
    let topLayerInfo = {
      maxZIndex: -Infinity,
      topLayerElements: [],
      modalDetected: false,
    };

    // Check what's actually visible by testing screen center
    const centerElement = document.elementFromPoint(
      window.innerWidth / 2,
      window.innerHeight / 2
    );

    if (centerElement) {
      // Walk up the DOM tree to find the highest z-index container
      let current = centerElement;
      while (current && current !== document.body) {
        const styles = window.getComputedStyle(current);
        const zIndex =
          styles.zIndex === "auto" ? 0 : parseInt(styles.zIndex) || 0;

        if (zIndex > topLayerInfo.maxZIndex) {
          topLayerInfo.maxZIndex = zIndex;
        }

        // Check if this looks like a modal (common modal indicators)
        if (styles.position === "fixed" && zIndex > 999) {
          topLayerInfo.modalDetected = true;
        }

        current = current.parentElement;
      }
    }

    return topLayerInfo;
  }

  // Make functions globally available
  window.showVisibleElements = showVisibleElements;
  window.highlightVisibleElements = highlightVisibleElements;
  window.getTopmostElement = getTopmostElement;
  window.getCurrentTopLayer = getCurrentTopLayer;

  const visibleElements = highlightVisibleElements();
  return visibleElements || [];
})();
