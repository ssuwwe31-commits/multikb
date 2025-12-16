import {
  Fragment,
  computed,
  createTextVNode,
  createVNode,
  defineComponent,
  nextTick,
  reactive,
  ref,
  watch,
  watchEffect
} from "./chunk-EWHTERDA.js";
import "./chunk-Q4XP6UTR.js";

// node_modules/vue-json-pretty/esm/vue-json-pretty.js
var t = { 207: (e, t2, n2) => {
  e.exports = n2(452);
}, 452: (e) => {
  var t2 = function(e2) {
    var t3, n2 = Object.prototype, r2 = n2.hasOwnProperty, o2 = "function" == typeof Symbol ? Symbol : {}, a2 = o2.iterator || "@@iterator", i2 = o2.asyncIterator || "@@asyncIterator", c2 = o2.toStringTag || "@@toStringTag";
    function l2(e3, t4, n3) {
      return Object.defineProperty(e3, t4, { value: n3, enumerable: true, configurable: true, writable: true }), e3[t4];
    }
    try {
      l2({}, "");
    } catch (e3) {
      l2 = function(e4, t4, n3) {
        return e4[t4] = n3;
      };
    }
    function u2(e3, t4, n3, r3) {
      var o3 = t4 && t4.prototype instanceof y2 ? t4 : y2, a3 = Object.create(o3.prototype), i3 = new V2(r3 || []);
      return a3._invoke = /* @__PURE__ */ function(e4, t5, n4) {
        var r4 = s2;
        return function(o4, a4) {
          if (r4 === f2) throw new Error("Generator is already running");
          if (r4 === p2) {
            if ("throw" === o4) throw a4;
            return P2();
          }
          for (n4.method = o4, n4.arg = a4; ; ) {
            var i4 = n4.delegate;
            if (i4) {
              var c3 = j2(i4, n4);
              if (c3) {
                if (c3 === v2) continue;
                return c3;
              }
            }
            if ("next" === n4.method) n4.sent = n4._sent = n4.arg;
            else if ("throw" === n4.method) {
              if (r4 === s2) throw r4 = p2, n4.arg;
              n4.dispatchException(n4.arg);
            } else "return" === n4.method && n4.abrupt("return", n4.arg);
            r4 = f2;
            var l3 = d2(e4, t5, n4);
            if ("normal" === l3.type) {
              if (r4 = n4.done ? p2 : h2, l3.arg === v2) continue;
              return { value: l3.arg, done: n4.done };
            }
            "throw" === l3.type && (r4 = p2, n4.method = "throw", n4.arg = l3.arg);
          }
        };
      }(e3, n3, i3), a3;
    }
    function d2(e3, t4, n3) {
      try {
        return { type: "normal", arg: e3.call(t4, n3) };
      } catch (e4) {
        return { type: "throw", arg: e4 };
      }
    }
    e2.wrap = u2;
    var s2 = "suspendedStart", h2 = "suspendedYield", f2 = "executing", p2 = "completed", v2 = {};
    function y2() {
    }
    function g2() {
    }
    function m2() {
    }
    var b2 = {};
    l2(b2, a2, function() {
      return this;
    });
    var w2 = Object.getPrototypeOf, N2 = w2 && w2(w2(L2([])));
    N2 && N2 !== n2 && r2.call(N2, a2) && (b2 = N2);
    var k2 = m2.prototype = y2.prototype = Object.create(b2);
    function C2(e3) {
      ["next", "throw", "return"].forEach(function(t4) {
        l2(e3, t4, function(e4) {
          return this._invoke(t4, e4);
        });
      });
    }
    function x2(e3, t4) {
      function n3(o4, a3, i3, c3) {
        var l3 = d2(e3[o4], e3, a3);
        if ("throw" !== l3.type) {
          var u3 = l3.arg, s3 = u3.value;
          return s3 && "object" == typeof s3 && r2.call(s3, "__await") ? t4.resolve(s3.__await).then(function(e4) {
            n3("next", e4, i3, c3);
          }, function(e4) {
            n3("throw", e4, i3, c3);
          }) : t4.resolve(s3).then(function(e4) {
            u3.value = e4, i3(u3);
          }, function(e4) {
            return n3("throw", e4, i3, c3);
          });
        }
        c3(l3.arg);
      }
      var o3;
      this._invoke = function(e4, r3) {
        function a3() {
          return new t4(function(t5, o4) {
            n3(e4, r3, t5, o4);
          });
        }
        return o3 = o3 ? o3.then(a3, a3) : a3();
      };
    }
    function j2(e3, n3) {
      var r3 = e3.iterator[n3.method];
      if (r3 === t3) {
        if (n3.delegate = null, "throw" === n3.method) {
          if (e3.iterator.return && (n3.method = "return", n3.arg = t3, j2(e3, n3), "throw" === n3.method)) return v2;
          n3.method = "throw", n3.arg = new TypeError("The iterator does not provide a 'throw' method");
        }
        return v2;
      }
      var o3 = d2(r3, e3.iterator, n3.arg);
      if ("throw" === o3.type) return n3.method = "throw", n3.arg = o3.arg, n3.delegate = null, v2;
      var a3 = o3.arg;
      return a3 ? a3.done ? (n3[e3.resultName] = a3.value, n3.next = e3.nextLoc, "return" !== n3.method && (n3.method = "next", n3.arg = t3), n3.delegate = null, v2) : a3 : (n3.method = "throw", n3.arg = new TypeError("iterator result is not an object"), n3.delegate = null, v2);
    }
    function S2(e3) {
      var t4 = { tryLoc: e3[0] };
      1 in e3 && (t4.catchLoc = e3[1]), 2 in e3 && (t4.finallyLoc = e3[2], t4.afterLoc = e3[3]), this.tryEntries.push(t4);
    }
    function O2(e3) {
      var t4 = e3.completion || {};
      t4.type = "normal", delete t4.arg, e3.completion = t4;
    }
    function V2(e3) {
      this.tryEntries = [{ tryLoc: "root" }], e3.forEach(S2, this), this.reset(true);
    }
    function L2(e3) {
      if (e3) {
        var n3 = e3[a2];
        if (n3) return n3.call(e3);
        if ("function" == typeof e3.next) return e3;
        if (!isNaN(e3.length)) {
          var o3 = -1, i3 = function n4() {
            for (; ++o3 < e3.length; ) if (r2.call(e3, o3)) return n4.value = e3[o3], n4.done = false, n4;
            return n4.value = t3, n4.done = true, n4;
          };
          return i3.next = i3;
        }
      }
      return { next: P2 };
    }
    function P2() {
      return { value: t3, done: true };
    }
    return g2.prototype = m2, l2(k2, "constructor", m2), l2(m2, "constructor", g2), g2.displayName = l2(m2, c2, "GeneratorFunction"), e2.isGeneratorFunction = function(e3) {
      var t4 = "function" == typeof e3 && e3.constructor;
      return !!t4 && (t4 === g2 || "GeneratorFunction" === (t4.displayName || t4.name));
    }, e2.mark = function(e3) {
      return Object.setPrototypeOf ? Object.setPrototypeOf(e3, m2) : (e3.__proto__ = m2, l2(e3, c2, "GeneratorFunction")), e3.prototype = Object.create(k2), e3;
    }, e2.awrap = function(e3) {
      return { __await: e3 };
    }, C2(x2.prototype), l2(x2.prototype, i2, function() {
      return this;
    }), e2.AsyncIterator = x2, e2.async = function(t4, n3, r3, o3, a3) {
      void 0 === a3 && (a3 = Promise);
      var i3 = new x2(u2(t4, n3, r3, o3), a3);
      return e2.isGeneratorFunction(n3) ? i3 : i3.next().then(function(e3) {
        return e3.done ? e3.value : i3.next();
      });
    }, C2(k2), l2(k2, c2, "Generator"), l2(k2, a2, function() {
      return this;
    }), l2(k2, "toString", function() {
      return "[object Generator]";
    }), e2.keys = function(e3) {
      var t4 = [];
      for (var n3 in e3) t4.push(n3);
      return t4.reverse(), function n4() {
        for (; t4.length; ) {
          var r3 = t4.pop();
          if (r3 in e3) return n4.value = r3, n4.done = false, n4;
        }
        return n4.done = true, n4;
      };
    }, e2.values = L2, V2.prototype = { constructor: V2, reset: function(e3) {
      if (this.prev = 0, this.next = 0, this.sent = this._sent = t3, this.done = false, this.delegate = null, this.method = "next", this.arg = t3, this.tryEntries.forEach(O2), !e3) for (var n3 in this) "t" === n3.charAt(0) && r2.call(this, n3) && !isNaN(+n3.slice(1)) && (this[n3] = t3);
    }, stop: function() {
      this.done = true;
      var e3 = this.tryEntries[0].completion;
      if ("throw" === e3.type) throw e3.arg;
      return this.rval;
    }, dispatchException: function(e3) {
      if (this.done) throw e3;
      var n3 = this;
      function o3(r3, o4) {
        return c3.type = "throw", c3.arg = e3, n3.next = r3, o4 && (n3.method = "next", n3.arg = t3), !!o4;
      }
      for (var a3 = this.tryEntries.length - 1; a3 >= 0; --a3) {
        var i3 = this.tryEntries[a3], c3 = i3.completion;
        if ("root" === i3.tryLoc) return o3("end");
        if (i3.tryLoc <= this.prev) {
          var l3 = r2.call(i3, "catchLoc"), u3 = r2.call(i3, "finallyLoc");
          if (l3 && u3) {
            if (this.prev < i3.catchLoc) return o3(i3.catchLoc, true);
            if (this.prev < i3.finallyLoc) return o3(i3.finallyLoc);
          } else if (l3) {
            if (this.prev < i3.catchLoc) return o3(i3.catchLoc, true);
          } else {
            if (!u3) throw new Error("try statement without catch or finally");
            if (this.prev < i3.finallyLoc) return o3(i3.finallyLoc);
          }
        }
      }
    }, abrupt: function(e3, t4) {
      for (var n3 = this.tryEntries.length - 1; n3 >= 0; --n3) {
        var o3 = this.tryEntries[n3];
        if (o3.tryLoc <= this.prev && r2.call(o3, "finallyLoc") && this.prev < o3.finallyLoc) {
          var a3 = o3;
          break;
        }
      }
      a3 && ("break" === e3 || "continue" === e3) && a3.tryLoc <= t4 && t4 <= a3.finallyLoc && (a3 = null);
      var i3 = a3 ? a3.completion : {};
      return i3.type = e3, i3.arg = t4, a3 ? (this.method = "next", this.next = a3.finallyLoc, v2) : this.complete(i3);
    }, complete: function(e3, t4) {
      if ("throw" === e3.type) throw e3.arg;
      return "break" === e3.type || "continue" === e3.type ? this.next = e3.arg : "return" === e3.type ? (this.rval = this.arg = e3.arg, this.method = "return", this.next = "end") : "normal" === e3.type && t4 && (this.next = t4), v2;
    }, finish: function(e3) {
      for (var t4 = this.tryEntries.length - 1; t4 >= 0; --t4) {
        var n3 = this.tryEntries[t4];
        if (n3.finallyLoc === e3) return this.complete(n3.completion, n3.afterLoc), O2(n3), v2;
      }
    }, catch: function(e3) {
      for (var t4 = this.tryEntries.length - 1; t4 >= 0; --t4) {
        var n3 = this.tryEntries[t4];
        if (n3.tryLoc === e3) {
          var r3 = n3.completion;
          if ("throw" === r3.type) {
            var o3 = r3.arg;
            O2(n3);
          }
          return o3;
        }
      }
      throw new Error("illegal catch attempt");
    }, delegateYield: function(e3, n3, r3) {
      return this.delegate = { iterator: L2(e3), resultName: n3, nextLoc: r3 }, "next" === this.method && (this.arg = t3), v2;
    } }, e2;
  }(e.exports);
  try {
    regeneratorRuntime = t2;
  } catch (e2) {
    "object" == typeof globalThis ? globalThis.regeneratorRuntime = t2 : Function("r", "regeneratorRuntime = r")(t2);
  }
} };
var n = {};
function r(e) {
  var o2 = n[e];
  if (void 0 !== o2) return o2.exports;
  var a2 = n[e] = { exports: {} };
  return t[e](a2, a2.exports, r), a2.exports;
}
r.n = (e) => {
  var t2 = e && e.__esModule ? () => e.default : () => e;
  return r.d(t2, { a: t2 }), t2;
}, r.d = (e, t2) => {
  for (var n2 in t2) r.o(t2, n2) && !r.o(e, n2) && Object.defineProperty(e, n2, { enumerable: true, get: t2[n2] });
}, r.o = (e, t2) => Object.prototype.hasOwnProperty.call(e, t2);
var o = {};
function a(e, t2) {
  (null == t2 || t2 > e.length) && (t2 = e.length);
  for (var n2 = 0, r2 = new Array(t2); n2 < t2; n2++) r2[n2] = e[n2];
  return r2;
}
function i(e, t2) {
  if (e) {
    if ("string" == typeof e) return a(e, t2);
    var n2 = Object.prototype.toString.call(e).slice(8, -1);
    return "Object" === n2 && e.constructor && (n2 = e.constructor.name), "Map" === n2 || "Set" === n2 ? Array.from(e) : "Arguments" === n2 || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n2) ? a(e, t2) : void 0;
  }
}
function c(e) {
  return function(e2) {
    if (Array.isArray(e2)) return a(e2);
  }(e) || function(e2) {
    if ("undefined" != typeof Symbol && null != e2[Symbol.iterator] || null != e2["@@iterator"]) return Array.from(e2);
  }(e) || i(e) || function() {
    throw new TypeError("Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
  }();
}
function l(e, t2, n2) {
  return t2 in e ? Object.defineProperty(e, t2, { value: n2, enumerable: true, configurable: true, writable: true }) : e[t2] = n2, e;
}
r.d(o, { A: () => L });
var u = (f = { Fragment: () => Fragment, computed: () => computed, createTextVNode: () => createTextVNode, createVNode: () => createVNode, defineComponent: () => defineComponent, nextTick: () => nextTick, reactive: () => reactive, ref: () => ref, watch: () => watch, watchEffect: () => watchEffect }, p = {}, r.d(p, f), p);
var d = (0, u.defineComponent)({ props: { data: { required: true, type: String }, onClick: Function }, render: function() {
  var e = this.data, t2 = this.onClick;
  return (0, u.createVNode)("span", { class: "vjs-tree-brackets", onClick: t2 }, [e]);
} });
var s = (0, u.defineComponent)({ emits: ["change", "update:modelValue"], props: { checked: { type: Boolean, default: false }, isMultiple: Boolean, onChange: Function }, setup: function(e, t2) {
  var n2 = t2.emit;
  return { uiType: (0, u.computed)(function() {
    return e.isMultiple ? "checkbox" : "radio";
  }), model: (0, u.computed)({ get: function() {
    return e.checked;
  }, set: function(e2) {
    return n2("update:modelValue", e2);
  } }) };
}, render: function() {
  var e = this.uiType, t2 = this.model, n2 = this.$emit;
  return (0, u.createVNode)("label", { class: ["vjs-check-controller", t2 ? "is-checked" : ""], onClick: function(e2) {
    return e2.stopPropagation();
  } }, [(0, u.createVNode)("span", { class: "vjs-check-controller-inner is-".concat(e) }, null), (0, u.createVNode)("input", { checked: t2, class: "vjs-check-controller-original is-".concat(e), type: e, onChange: function() {
    return n2("change", t2);
  } }, null)]);
} });
var h = (0, u.defineComponent)({ props: { nodeType: { required: true, type: String }, onClick: Function }, render: function() {
  var e = this.nodeType, t2 = this.onClick, n2 = "objectStart" === e || "arrayStart" === e;
  return n2 || "objectCollapsed" === e || "arrayCollapsed" === e ? (0, u.createVNode)("span", { class: "vjs-carets vjs-carets-".concat(n2 ? "open" : "close"), onClick: t2 }, [(0, u.createVNode)("svg", { viewBox: "0 0 1024 1024", focusable: "false", "data-icon": "caret-down", width: "1em", height: "1em", fill: "currentColor", "aria-hidden": "true" }, [(0, u.createVNode)("path", { d: "M840.4 300H183.6c-19.7 0-30.7 20.8-18.5 35l328.4 380.8c9.4 10.9 27.5 10.9 37 0L858.9 335c12.2-14.2 1.2-35-18.5-35z" }, null)])]) : null;
} });
var f;
var p;
function v(e) {
  return v = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(e2) {
    return typeof e2;
  } : function(e2) {
    return e2 && "function" == typeof Symbol && e2.constructor === Symbol && e2 !== Symbol.prototype ? "symbol" : typeof e2;
  }, v(e);
}
function y(e) {
  return Object.prototype.toString.call(e).slice(8, -1).toLowerCase();
}
function g(e) {
  var t2 = arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : "root", n2 = arguments.length > 2 && void 0 !== arguments[2] ? arguments[2] : 0, r2 = (arguments.length > 3 ? arguments[3] : void 0) || {}, o2 = r2.key, a2 = r2.index, i2 = r2.type, c2 = void 0 === i2 ? "content" : i2, l2 = r2.showComma, u2 = void 0 !== l2 && l2, d2 = r2.length, s2 = void 0 === d2 ? 1 : d2, h2 = y(e);
  if ("array" === h2) {
    var f2 = m(e.map(function(e2, r3, o3) {
      return g(e2, "".concat(t2, "[").concat(r3, "]"), n2 + 1, { index: r3, showComma: r3 !== o3.length - 1, length: s2, type: c2 });
    }));
    return [g("[", t2, n2, { showComma: false, key: o2, length: e.length, type: "arrayStart" })[0]].concat(f2, g("]", t2, n2, { showComma: u2, length: e.length, type: "arrayEnd" })[0]);
  }
  if ("object" === h2) {
    var p2 = Object.keys(e), v2 = m(p2.map(function(r3, o3, a3) {
      return g(e[r3], /^[a-zA-Z_]\w*$/.test(r3) ? "".concat(t2, ".").concat(r3) : "".concat(t2, '["').concat(r3, '"]'), n2 + 1, { key: r3, showComma: o3 !== a3.length - 1, length: s2, type: c2 });
    }));
    return [g("{", t2, n2, { showComma: false, key: o2, index: a2, length: p2.length, type: "objectStart" })[0]].concat(v2, g("}", t2, n2, { showComma: u2, length: p2.length, type: "objectEnd" })[0]);
  }
  return [{ content: e, level: n2, key: o2, index: a2, path: t2, showComma: u2, length: s2, type: c2 }];
}
function m(e) {
  if ("function" == typeof Array.prototype.flat) return e.flat();
  for (var t2 = c(e), n2 = []; t2.length; ) {
    var r2 = t2.shift();
    Array.isArray(r2) ? t2.unshift.apply(t2, c(r2)) : n2.push(r2);
  }
  return n2;
}
function b(e) {
  var t2 = arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : /* @__PURE__ */ new WeakMap();
  if (null == e) return e;
  if (e instanceof Date) return new Date(e);
  if (e instanceof RegExp) return new RegExp(e);
  if ("object" !== v(e)) return e;
  if (t2.get(e)) return t2.get(e);
  if (Array.isArray(e)) {
    var n2 = e.map(function(e2) {
      return b(e2, t2);
    });
    return t2.set(e, n2), n2;
  }
  var r2 = {};
  for (var o2 in e) r2[o2] = b(e[o2], t2);
  return t2.set(e, r2), r2;
}
function w(e, t2, n2, r2, o2, a2, i2) {
  try {
    var c2 = e[a2](i2), l2 = c2.value;
  } catch (e2) {
    return void n2(e2);
  }
  c2.done ? t2(l2) : Promise.resolve(l2).then(r2, o2);
}
var N = r(207);
var k = r.n(N);
function C(e, t2) {
  var n2 = Object.keys(e);
  if (Object.getOwnPropertySymbols) {
    var r2 = Object.getOwnPropertySymbols(e);
    t2 && (r2 = r2.filter(function(t3) {
      return Object.getOwnPropertyDescriptor(e, t3).enumerable;
    })), n2.push.apply(n2, r2);
  }
  return n2;
}
function x(e) {
  for (var t2 = 1; t2 < arguments.length; t2++) {
    var n2 = null != arguments[t2] ? arguments[t2] : {};
    t2 % 2 ? C(Object(n2), true).forEach(function(t3) {
      l(e, t3, n2[t3]);
    }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(n2)) : C(Object(n2)).forEach(function(t3) {
      Object.defineProperty(e, t3, Object.getOwnPropertyDescriptor(n2, t3));
    });
  }
  return e;
}
var j = { data: { type: [String, Number, Boolean, Array, Object], default: null }, rootPath: { type: String, default: "root" }, indent: { type: Number, default: 2 }, showLength: { type: Boolean, default: false }, showDoubleQuotes: { type: Boolean, default: true }, renderNodeKey: Function, renderNodeValue: Function, renderNodeActions: { type: [Boolean, Function], default: void 0 }, selectableType: String, showSelectController: { type: Boolean, default: false }, showLine: { type: Boolean, default: true }, showLineNumber: { type: Boolean, default: false }, selectOnClickNode: { type: Boolean, default: true }, nodeSelectable: { type: Function, default: function() {
  return true;
} }, highlightSelectedNode: { type: Boolean, default: true }, showIcon: { type: Boolean, default: false }, theme: { type: String, default: "light" }, showKeyValueSpace: { type: Boolean, default: true }, editable: { type: Boolean, default: false }, editableTrigger: { type: String, default: "click" }, onNodeClick: { type: Function }, onNodeMouseover: { type: Function }, onBracketsClick: { type: Function }, onIconClick: { type: Function }, onValueChange: { type: Function } };
var S = (0, u.defineComponent)({ name: "TreeNode", props: x(x({}, j), {}, { node: { type: Object, required: true }, collapsed: Boolean, checked: Boolean, style: Object, onSelectedChange: { type: Function } }), emits: ["nodeClick", "nodeMouseover", "bracketsClick", "iconClick", "selectedChange", "valueChange"], setup: function(e, t2) {
  var n2 = t2.emit, r2 = (0, u.computed)(function() {
    return y(e.node.content);
  }), o2 = (0, u.computed)(function() {
    return "vjs-value vjs-value-".concat(r2.value);
  }), a2 = (0, u.computed)(function() {
    return e.showDoubleQuotes ? '"'.concat(e.node.key, '"') : e.node.key;
  }), i2 = (0, u.computed)(function() {
    return "multiple" === e.selectableType;
  }), c2 = (0, u.computed)(function() {
    return "single" === e.selectableType;
  }), f2 = (0, u.computed)(function() {
    return e.nodeSelectable(e.node) && (i2.value || c2.value);
  }), p2 = (0, u.reactive)({ editing: false }), v2 = function(t3) {
    var r3, o3, a3 = "null" === (o3 = null === (r3 = t3.target) || void 0 === r3 ? void 0 : r3.value) ? null : "undefined" === o3 ? void 0 : "true" === o3 || "false" !== o3 && (o3[0] + o3[o3.length - 1] === '""' || o3[0] + o3[o3.length - 1] === "''" ? o3.slice(1, -1) : "number" == typeof Number(o3) && !isNaN(Number(o3)) || "NaN" === o3 ? Number(o3) : o3);
    n2("valueChange", a3, e.node.path);
  }, g2 = (0, u.computed)(function() {
    var t3, n3 = null === (t3 = e.node) || void 0 === t3 ? void 0 : t3.content;
    return null === n3 ? n3 = "null" : void 0 === n3 && (n3 = "undefined"), "string" === r2.value ? '"'.concat(n3, '"') : n3 + "";
  }), m2 = function() {
    var t3 = e.renderNodeValue;
    return t3 ? t3({ node: e.node, defaultValue: g2.value }) : g2.value;
  }, b2 = function() {
    n2("bracketsClick", !e.collapsed, e.node);
  }, N2 = function() {
    n2("iconClick", !e.collapsed, e.node);
  }, C2 = function() {
    n2("selectedChange", e.node);
  }, x2 = function() {
    n2("nodeClick", e.node), f2.value && e.selectOnClickNode && n2("selectedChange", e.node);
  }, j2 = function() {
    n2("nodeMouseover", e.node);
  }, S2 = function(t3) {
    if (e.editable && !p2.editing) {
      p2.editing = true;
      var n3 = function e2(n4) {
        var r3;
        n4.target !== t3.target && (null === (r3 = n4.target) || void 0 === r3 ? void 0 : r3.parentElement) !== t3.target && (p2.editing = false, document.removeEventListener("click", e2));
      };
      document.removeEventListener("click", n3), document.addEventListener("click", n3);
    }
  }, O2 = function() {
    var e2 = (0, u.ref)(false), t3 = function() {
      var t4, n3 = (t4 = k().mark(function t5(n4) {
        return k().wrap(function(t6) {
          for (; ; ) switch (t6.prev = t6.next) {
            case 0:
              return t6.prev = 0, t6.next = 3, navigator.clipboard.writeText(n4);
            case 3:
              e2.value = true, setTimeout(function() {
                e2.value = false;
              }, 300), t6.next = 10;
              break;
            case 7:
              t6.prev = 7, t6.t0 = t6.catch(0), console.error("[vue-json-pretty] Copy failed: ", t6.t0);
            case 10:
            case "end":
              return t6.stop();
          }
        }, t5, null, [[0, 7]]);
      }), function() {
        var e3 = this, n4 = arguments;
        return new Promise(function(r3, o3) {
          var a3 = t4.apply(e3, n4);
          function i3(e4) {
            w(a3, r3, o3, i3, c3, "next", e4);
          }
          function c3(e4) {
            w(a3, r3, o3, i3, c3, "throw", e4);
          }
          i3(void 0);
        });
      });
      return function(e3) {
        return n3.apply(this, arguments);
      };
    }();
    return { copy: t3 };
  }().copy, V2 = function() {
    var t3 = e.node, n3 = t3.key, r3 = t3.path, o3 = e.rootPath, a3 = new Function("data", "return data".concat(r3.slice(o3.length)))(e.data), i3 = JSON.stringify(n3 ? l({}, n3, a3) : a3, null, 2);
    O2(i3);
  }, L2 = function() {
    var t3 = e.renderNodeActions;
    if (!t3) return null;
    var n3 = { copy: V2 };
    return "function" == typeof t3 ? t3({ node: e.node, defaultActions: n3 }) : (0, u.createVNode)("span", { onClick: V2, class: "vjs-tree-node-actions-item" }, [(0, u.createTextVNode)("copy")]);
  };
  return function() {
    var t3, n3 = e.node;
    return (0, u.createVNode)("div", { class: { "vjs-tree-node": true, "has-selector": e.showSelectController, "has-carets": e.showIcon, "is-highlight": e.highlightSelectedNode && e.checked, dark: "dark" === e.theme }, onClick: x2, onMouseover: j2, style: e.style }, [e.showLineNumber && (0, u.createVNode)("span", { class: "vjs-node-index" }, [n3.id + 1]), e.showSelectController && f2.value && "objectEnd" !== n3.type && "arrayEnd" !== n3.type && (0, u.createVNode)(s, { isMultiple: i2.value, checked: e.checked, onChange: C2 }, null), (0, u.createVNode)("div", { class: "vjs-indent" }, [Array.from(Array(n3.level)).map(function(t4, n4) {
      return (0, u.createVNode)("div", { key: n4, class: { "vjs-indent-unit": true, "has-line": e.showLine } }, [Array.from(Array(e.indent)).map(function() {
        return (0, u.createVNode)(u.Fragment, null, [(0, u.createTextVNode)(" ")]);
      })]);
    }), e.showIcon && (0, u.createVNode)(h, { nodeType: n3.type, onClick: N2 }, null)]), n3.key && (0, u.createVNode)("span", { class: "vjs-key" }, [(t3 = e.renderNodeKey, t3 ? t3({ node: e.node, defaultKey: a2.value || "" }) : a2.value), (0, u.createVNode)("span", { class: "vjs-colon" }, [":".concat(e.showKeyValueSpace ? " " : "")])]), (0, u.createVNode)("span", null, ["content" !== n3.type && n3.content ? (0, u.createVNode)(d, { data: n3.content.toString(), onClick: b2 }, null) : (0, u.createVNode)("span", { class: o2.value, onClick: !e.editable || e.editableTrigger && "click" !== e.editableTrigger ? void 0 : S2, onDblclick: e.editable && "dblclick" === e.editableTrigger ? S2 : void 0 }, [e.editable && p2.editing ? (0, u.createVNode)("input", { value: g2.value, onChange: v2, style: { padding: "3px 8px", border: "1px solid #eee", boxShadow: "none", boxSizing: "border-box", borderRadius: 5, fontFamily: "inherit" } }, null) : m2()]), n3.showComma && (0, u.createVNode)("span", null, [","]), e.showLength && e.collapsed && (0, u.createVNode)("span", { class: "vjs-comment" }, [(0, u.createTextVNode)(" // "), n3.length, (0, u.createTextVNode)(" items ")])]), e.renderNodeActions && (0, u.createVNode)("span", { class: "vjs-tree-node-actions" }, [L2()])]);
  };
} });
function O(e, t2) {
  var n2 = Object.keys(e);
  if (Object.getOwnPropertySymbols) {
    var r2 = Object.getOwnPropertySymbols(e);
    t2 && (r2 = r2.filter(function(t3) {
      return Object.getOwnPropertyDescriptor(e, t3).enumerable;
    })), n2.push.apply(n2, r2);
  }
  return n2;
}
function V(e) {
  for (var t2 = 1; t2 < arguments.length; t2++) {
    var n2 = null != arguments[t2] ? arguments[t2] : {};
    t2 % 2 ? O(Object(n2), true).forEach(function(t3) {
      l(e, t3, n2[t3]);
    }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(n2)) : O(Object(n2)).forEach(function(t3) {
      Object.defineProperty(e, t3, Object.getOwnPropertyDescriptor(n2, t3));
    });
  }
  return e;
}
var L = (0, u.defineComponent)({ name: "Tree", props: V(V({}, j), {}, { collapsedNodeLength: { type: Number, default: 1 / 0 }, deep: { type: Number, default: 1 / 0 }, pathCollapsible: { type: Function, default: function() {
  return false;
} }, virtual: { type: Boolean, default: false }, height: { type: Number, default: 400 }, itemHeight: { type: Number, default: 20 }, dynamicHeight: { type: Boolean, default: true }, selectedValue: { type: [String, Array], default: function() {
  return "";
} }, collapsedOnClickBrackets: { type: Boolean, default: true }, style: Object, onSelectedChange: { type: Function }, theme: { type: String, default: "light" } }), slots: ["renderNodeKey", "renderNodeValue", "renderNodeActions"], emits: ["nodeClick", "nodeMouseover", "bracketsClick", "iconClick", "selectedChange", "update:selectedValue", "update:data"], setup: function(e, t2) {
  var n2 = t2.emit, r2 = t2.slots, o2 = (0, u.ref)(), a2 = (0, u.computed)(function() {
    return g(e.data, e.rootPath);
  }), d2 = function(t3, n3) {
    return a2.value.reduce(function(r3, o3) {
      var a3, i2 = o3.level >= t3 || o3.length >= n3, c2 = null === (a3 = e.pathCollapsible) || void 0 === a3 ? void 0 : a3.call(e, o3);
      return "objectStart" !== o3.type && "arrayStart" !== o3.type || !i2 && !c2 ? r3 : V(V({}, r3), {}, l({}, o3.path, 1));
    }, {});
  }, s2 = (0, u.reactive)({ translateY: 0, visibleData: null, hiddenPaths: d2(e.deep, e.collapsedNodeLength), startIndex: 0, endIndex: 0 }), h2 = [], f2 = [], p2 = 0, v2 = {}, y2 = function(t3) {
    h2 = Array(t3).fill(0).map(function() {
      return e.itemHeight || 20;
    }), (f2 = new Array(t3 + 1))[0] = 0;
    for (var n3 = 0; n3 < t3; n3++) f2[n3 + 1] = f2[n3] + h2[n3];
    p2 = f2[t3] || 0;
  }, m2 = function(e2) {
    var t3 = h2.length;
    e2 < 0 && (e2 = 0), e2 > t3 && (e2 = t3);
    for (var n3 = e2; n3 < t3; n3++) f2[n3 + 1] = f2[n3] + h2[n3];
    p2 = f2[t3] || 0;
  }, w2 = function(e2, t3) {
    for (var n3 = 0, r3 = e2.length - 1; n3 < r3; ) {
      var o3 = n3 + r3 >>> 1;
      e2[o3] < t3 ? n3 = o3 + 1 : r3 = o3;
    }
    return n3;
  }, N2 = (0, u.computed)(function() {
    for (var e2 = null, t3 = [], n3 = a2.value.length, r3 = 0; r3 < n3; r3++) {
      var o3 = V(V({}, a2.value[r3]), {}, { id: r3 }), i2 = s2.hiddenPaths[o3.path];
      if (e2 && e2.path === o3.path) {
        var c2 = "objectStart" === e2.type, l2 = V(V(V({}, o3), e2), {}, { showComma: o3.showComma, content: c2 ? "{...}" : "[...]", type: c2 ? "objectCollapsed" : "arrayCollapsed" });
        e2 = null, t3.push(l2);
      } else {
        if (i2 && !e2) {
          e2 = o3;
          continue;
        }
        if (e2) continue;
        t3.push(o3);
      }
    }
    return t3;
  }), k2 = (0, u.computed)(function() {
    var t3 = e.selectedValue;
    return t3 && "multiple" === e.selectableType && Array.isArray(t3) ? t3 : [t3];
  }), C2 = (0, u.computed)(function() {
    return !e.selectableType || e.selectOnClickNode || e.showSelectController ? "" : "When selectableType is not null, selectOnClickNode and showSelectController cannot be false at the same time, because this will cause the selection to fail.";
  }), x2 = (0, u.computed)(function() {
    return e.dynamicHeight ? p2 || 0 : N2.value.length * e.itemHeight;
  }), j2 = function t3() {
    var n3 = N2.value;
    if (n3) if (e.virtual) {
      var r3, a3 = (null === (r3 = o2.value) || void 0 === r3 ? void 0 : r3.scrollTop) || 0;
      if (e.dynamicHeight) {
        h2.length !== n3.length && y2(n3.length);
        var i2 = function(e2) {
          var t4 = w2(f2, e2 + 1e-4);
          return Math.max(0, Math.min(t4 - 1, h2.length - 1));
        }(a3), c2 = function(e2, t4) {
          var n4 = w2(f2, e2 + t4);
          return Math.max(0, Math.min(n4 + 1, h2.length));
        }(a3, e.height), l2 = Math.max(0, i2 - 5), d3 = Math.min(n3.length, c2 + 5);
        s2.startIndex = l2, s2.endIndex = d3, s2.translateY = f2[l2] || 0, s2.visibleData = n3.slice(l2, d3), (0, u.nextTick)().then(function() {
          for (var e2 = false, n4 = s2.startIndex; n4 < s2.endIndex; n4++) {
            var r4 = v2[n4];
            if (r4) {
              var o3 = r4.offsetHeight;
              o3 && h2[n4] !== o3 && (h2[n4] = o3, f2[n4 + 1] = f2[n4] + h2[n4], m2(n4 + 1), e2 = true);
            }
          }
          e2 && t3();
        });
      } else {
        var p3 = e.height / e.itemHeight, g2 = Math.floor(a3 / e.itemHeight), b2 = g2 < 0 ? 0 : g2 + p3 > n3.length ? n3.length - p3 : g2;
        b2 < 0 && (b2 = 0);
        var k3 = b2 + p3;
        s2.translateY = b2 * e.itemHeight, s2.startIndex = b2, s2.endIndex = k3, s2.visibleData = n3.slice(b2, k3);
      }
    } else s2.translateY = 0, s2.startIndex = 0, s2.endIndex = n3.length, s2.visibleData = n3;
  }, O2 = null, L2 = function() {
    O2 && cancelAnimationFrame(O2), O2 = requestAnimationFrame(function() {
      j2();
    });
  }, P2 = function(t3) {
    var r3, o3, a3 = t3.path, l2 = e.selectableType;
    if ("multiple" === l2) {
      var u2 = k2.value.findIndex(function(e2) {
        return e2 === a3;
      }), d3 = c(k2.value);
      -1 !== u2 ? d3.splice(u2, 1) : d3.push(a3), n2("update:selectedValue", d3), n2("selectedChange", d3, c(k2.value));
    } else if ("single" === l2 && k2.value[0] !== a3) {
      var s3 = (r3 = k2.value, o3 = 1, function(e2) {
        if (Array.isArray(e2)) return e2;
      }(r3) || function(e2, t4) {
        var n3 = null == e2 ? null : "undefined" != typeof Symbol && e2[Symbol.iterator] || e2["@@iterator"];
        if (null != n3) {
          var r4, o4, a4 = [], i2 = true, c2 = false;
          try {
            for (n3 = n3.call(e2); !(i2 = (r4 = n3.next()).done) && (a4.push(r4.value), !t4 || a4.length !== t4); i2 = true) ;
          } catch (e3) {
            c2 = true, o4 = e3;
          } finally {
            try {
              i2 || null == n3.return || n3.return();
            } finally {
              if (c2) throw o4;
            }
          }
          return a4;
        }
      }(r3, o3) || i(r3, o3) || function() {
        throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
      }())[0], h3 = a3;
      n2("update:selectedValue", h3), n2("selectedChange", h3, s3);
    }
  }, T = function(e2) {
    n2("nodeClick", e2);
  }, E = function(e2) {
    n2("nodeMouseover", e2);
  }, A = function(e2, t3) {
    if (e2) s2.hiddenPaths = V(V({}, s2.hiddenPaths), {}, l({}, t3, 1));
    else {
      var n3 = V({}, s2.hiddenPaths);
      delete n3[t3], s2.hiddenPaths = n3;
    }
  }, F = function(t3, r3) {
    e.collapsedOnClickBrackets && A(t3, r3.path), n2("bracketsClick", t3, r3);
  }, I = function(e2, t3) {
    A(e2, t3.path), n2("iconClick", e2, t3);
  }, B = function(t3, r3) {
    var o3 = b(e.data), a3 = e.rootPath;
    new Function("data", "val", "data".concat(r3.slice(a3.length), "=val"))(o3, t3), n2("update:data", o3);
  };
  return (0, u.watchEffect)(function() {
    C2.value && function(e2) {
      throw new Error("[VueJSONPretty] ".concat(e2));
    }(C2.value);
  }), (0, u.watchEffect)(function() {
    N2.value && (e.virtual && e.dynamicHeight && h2.length !== N2.value.length && y2(N2.value.length), j2());
  }), (0, u.watch)(function() {
    return [e.dynamicHeight, e.itemHeight, a2.value.length];
  }, function() {
    e.virtual && e.dynamicHeight && (y2(N2.value.length), (0, u.nextTick)(j2));
  }), (0, u.watch)(function() {
    return e.deep;
  }, function(t3) {
    t3 && (s2.hiddenPaths = d2(t3, e.collapsedNodeLength));
  }), (0, u.watch)(function() {
    return e.collapsedNodeLength;
  }, function(t3) {
    t3 && (s2.hiddenPaths = d2(e.deep, t3));
  }), function() {
    var t3, n3, i2, c2, l2, d3 = null !== (t3 = e.renderNodeKey) && void 0 !== t3 ? t3 : r2.renderNodeKey, h3 = null !== (n3 = e.renderNodeValue) && void 0 !== n3 ? n3 : r2.renderNodeValue, f3 = null !== (i2 = null !== (c2 = e.renderNodeActions) && void 0 !== c2 ? c2 : r2.renderNodeActions) && void 0 !== i2 && i2, p3 = null === (l2 = s2.visibleData) || void 0 === l2 ? void 0 : l2.map(function(t4, n4) {
      var r3 = s2.startIndex + n4;
      return (0, u.createVNode)("div", { key: t4.id, ref: function(e2) {
        return function(e3, t5) {
          t5 ? v2[e3] = t5 : delete v2[e3];
        }(r3, e2 || null);
      } }, [(0, u.createVNode)(S, { data: e.data, rootPath: e.rootPath, indent: e.indent, node: t4, collapsed: !!s2.hiddenPaths[t4.path], theme: e.theme, showDoubleQuotes: e.showDoubleQuotes, showLength: e.showLength, checked: k2.value.includes(t4.path), selectableType: e.selectableType, showLine: e.showLine, showLineNumber: e.showLineNumber, showSelectController: e.showSelectController, selectOnClickNode: e.selectOnClickNode, nodeSelectable: e.nodeSelectable, highlightSelectedNode: e.highlightSelectedNode, editable: e.editable, editableTrigger: e.editableTrigger, showIcon: e.showIcon, showKeyValueSpace: e.showKeyValueSpace, renderNodeKey: d3, renderNodeValue: h3, renderNodeActions: f3, onNodeClick: T, onNodeMouseover: E, onBracketsClick: F, onIconClick: I, onSelectedChange: P2, onValueChange: B, class: e.dynamicHeight ? "dynamic-height" : void 0, style: e.dynamicHeight ? {} : e.itemHeight && 20 !== e.itemHeight ? { lineHeight: "".concat(e.itemHeight, "px") } : {} }, null)]);
    });
    return (0, u.createVNode)("div", { ref: o2, class: { "vjs-tree": true, "is-virtual": e.virtual, dark: "dark" === e.theme }, onScroll: e.virtual ? L2 : void 0, style: e.showLineNumber ? V({ paddingLeft: "".concat(12 * Number(a2.value.length.toString().length), "px") }, e.style) : e.style }, [e.virtual ? (0, u.createVNode)("div", { class: "vjs-tree-list", style: { height: "".concat(e.height, "px") } }, [(0, u.createVNode)("div", { class: "vjs-tree-list-holder", style: { height: "".concat(x2.value, "px") } }, [(0, u.createVNode)("div", { class: "vjs-tree-list-holder-inner", style: { transform: "translateY(".concat(s2.translateY, "px)") } }, [p3])])]) : p3]);
  };
} });
var P = o.A;
export {
  P as default
};
//# sourceMappingURL=vue-json-pretty.js.map
