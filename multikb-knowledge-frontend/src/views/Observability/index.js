"use strict";
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
Object.defineProperty(exports, "__esModule", { value: true });
var vue_1 = require("vue");
var element_plus_1 = require("element-plus");
var observability_1 = require("@/api/modules/observability");
var format_1 = require("@/utils/format");
var icons_vue_1 = require("@element-plus/icons-vue");
exports.default = (0, vue_1.defineComponent)({
    name: 'ObservabilityPage',
    components: {
        Monitor: icons_vue_1.Monitor,
        ArrowDown: icons_vue_1.ArrowDown,
        MoreFilled: icons_vue_1.MoreFilled,
        Edit: icons_vue_1.Edit,
        Delete: icons_vue_1.Delete,
        WarningFilled: icons_vue_1.WarningFilled,
        InfoFilled: icons_vue_1.InfoFilled,
        CircleCheckFilled: icons_vue_1.CircleCheckFilled,
        CircleCloseFilled: icons_vue_1.CircleCloseFilled,
        Document: icons_vue_1.Document,
        Setting: icons_vue_1.Setting,
        Bell: icons_vue_1.Bell,
        DataAnalysis: icons_vue_1.DataAnalysis,
        Clock: icons_vue_1.Clock,
        Box: icons_vue_1.Box,
        Connection: icons_vue_1.Connection,
        TrendCharts: icons_vue_1.TrendCharts
    },
    setup: function () {
        var _this = this;
        var activeTab = (0, vue_1.ref)('clusters');
        var pageLoading = (0, vue_1.ref)(false);
        var isAuthError = function (error) {
            var _a;
            var err = error;
            return !!((err === null || err === void 0 ? void 0 : err.isAuthError) || (err === null || err === void 0 ? void 0 : err.code) === 401 || ((_a = err === null || err === void 0 ? void 0 : err.response) === null || _a === void 0 ? void 0 : _a.status) === 401);
        };
        var PROM_AUTH_OPTIONS = [
            { label: '无认证', value: 'none' },
            { label: 'Basic', value: 'basic' },
            { label: 'Bearer Token', value: 'token' }
        ];
        var LOG_AUTH_OPTIONS = [
            { label: '无认证', value: 'none' },
            { label: 'Basic', value: 'basic' },
            { label: 'Bearer Token', value: 'token' }
        ];
        var FEEDBACK_OPTIONS = [
            {
                value: 'confirmed',
                label: '已确认根因',
                description: '确认诊断结论正确，并沉淀为知识库案例'
            },
            {
                value: 'continue_investigation',
                label: '继续排查',
                description: '当前结论不可信，需要继续执行后续步骤收集更多信息'
            },
            {
                value: 'custom',
                label: '其他反馈',
                description: '自定义反馈内容（需要填写具体说明）'
            }
        ];
        var createEmptyClusterForm = function () { return ({
            name: '',
            api_server: '',
            auth_type: 'token',
            auth_token: '',
            kubeconfig: '',
            client_cert: '',
            client_key: '',
            ca_cert: '',
            verify_ssl: true,
            prometheus_url: '',
            prometheus_auth_type: 'none',
            prometheus_username: '',
            prometheus_password: '',
            log_system: '',
            log_endpoint: '',
            log_auth_type: 'none',
            log_username: '',
            log_password: '',
            is_active: true
        }); };
        // 集群管理
        var clusters = (0, vue_1.ref)([]);
        var clusterPagination = (0, vue_1.reactive)({
            page: 1,
            size: 10,
            total: 0
        });
        var clusterDialog = (0, vue_1.reactive)({
            visible: false,
            editing: false,
            form: createEmptyClusterForm()
        });
        var clusterFormRef = (0, vue_1.ref)();
        var clusterRules = {
            name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
            api_server: [{ required: true, message: '请输入 API Server', trigger: 'blur' }]
        };
        (0, vue_1.watch)(function () { return clusterDialog.form.prometheus_auth_type; }, function (type) {
            if (type !== 'basic') {
                clusterDialog.form.prometheus_username = '';
            }
            if (type === 'none') {
                clusterDialog.form.prometheus_password = '';
            }
        });
        (0, vue_1.watch)(function () { return clusterDialog.form.prometheus_url; }, function (url) {
            if (!url) {
                clusterDialog.form.prometheus_auth_type = 'none';
                clusterDialog.form.prometheus_username = '';
                clusterDialog.form.prometheus_password = '';
            }
        });
        (0, vue_1.watch)(function () { return clusterDialog.form.log_auth_type; }, function (type) {
            if (type !== 'basic') {
                clusterDialog.form.log_username = '';
            }
            if (type === 'none') {
                clusterDialog.form.log_password = '';
            }
        });
        (0, vue_1.watch)(function () { return clusterDialog.form.log_system; }, function (system) {
            if (!system) {
                clusterDialog.form.log_auth_type = 'none';
                clusterDialog.form.log_username = '';
                clusterDialog.form.log_password = '';
            }
        });
        var loadClusters = function () { return __awaiter(_this, void 0, void 0, function () {
            var res, data, clusterList, error_1;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        pageLoading.value = true;
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, (0, observability_1.fetchClusters)({
                                page: clusterPagination.page,
                                size: clusterPagination.size
                            })];
                    case 2:
                        res = _b.sent();
                        data = (res === null || res === void 0 ? void 0 : res.data) || {};
                        clusterList = Array.isArray(data.list) ? data.list : [];
                        clusters.value = clusterList.filter(function (item) { return item && item.id && item.name; });
                        clusterPagination.total = (_a = data.total) !== null && _a !== void 0 ? _a : 0;
                        if (clusters.value.length && !resourceFilters.clusterId) {
                            resourceFilters.clusterId = clusters.value[0].id;
                            metricsForm.cluster_id = clusters.value[0].id;
                            logForm.cluster_id = clusters.value[0].id;
                            // 只有在对话框没有打开时才设置默认集群ID
                            if (!diagnosisDialog.visible) {
                                diagnosisDialog.form.cluster_id = clusters.value[0].id;
                            }
                        }
                        return [3 /*break*/, 5];
                    case 3:
                        error_1 = _b.sent();
                        console.error('[ERROR] 加载集群失败:', error_1);
                        if (!isAuthError(error_1)) {
                            element_plus_1.ElMessage.error('加载集群失败');
                        }
                        else {
                            clusters.value = [];
                            clusterPagination.total = 0;
                        }
                        return [3 /*break*/, 5];
                    case 4:
                        pageLoading.value = false;
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        }); };
        var openClusterDialog = function (record) {
            clusterDialog.editing = !!record;
            clusterDialog.visible = true;
            clusterDialog.form = record
                ? __assign(__assign(__assign({}, createEmptyClusterForm()), record), { auth_token: '', kubeconfig: '', client_cert: '', client_key: '', ca_cert: '', prometheus_password: '', log_password: '' }) : createEmptyClusterForm();
            (0, vue_1.nextTick)(function () {
                var _a;
                (_a = clusterFormRef.value) === null || _a === void 0 ? void 0 : _a.clearValidate();
            });
        };
        var buildClusterPayload = function (isEditing) {
            var payload = __assign({}, clusterDialog.form);
            if (payload.auth_type === 'kubeconfig') {
                payload.auth_token = undefined;
                if (!payload.kubeconfig) {
                    payload.kubeconfig = undefined;
                    if (!isEditing) {
                        throw new Error('KUBECONFIG_REQUIRED');
                    }
                }
            }
            else {
                payload.kubeconfig = undefined;
                if (!payload.auth_token) {
                    payload.auth_token = undefined;
                }
            }
            // 处理 Prometheus URL：空字符串转为 undefined
            if (!payload.prometheus_url || payload.prometheus_url.trim() === '') {
                payload.prometheus_url = undefined;
                payload.prometheus_auth_type = 'none';
                payload.prometheus_username = undefined;
                payload.prometheus_password = undefined;
            }
            else if (payload.prometheus_auth_type === 'basic') {
                if (!payload.prometheus_username) {
                    throw new Error('PROM_BASIC_REQUIRED');
                }
                if (!payload.prometheus_password) {
                    if (!isEditing) {
                        throw new Error('PROM_BASIC_REQUIRED');
                    }
                    payload.prometheus_password = undefined;
                }
            }
            else if (payload.prometheus_auth_type === 'token') {
                if (!payload.prometheus_password) {
                    if (!isEditing) {
                        throw new Error('PROM_TOKEN_REQUIRED');
                    }
                    payload.prometheus_password = undefined;
                }
                payload.prometheus_username = undefined;
            }
            else {
                payload.prometheus_username = undefined;
                payload.prometheus_password = undefined;
            }
            // 处理日志系统：如果未选择日志系统，清空相关字段
            if (!payload.log_system || payload.log_system.trim() === '') {
                payload.log_system = undefined;
                payload.log_endpoint = undefined;
                payload.log_auth_type = 'none';
                payload.log_username = undefined;
                payload.log_password = undefined;
            }
            else if (!payload.log_endpoint || payload.log_endpoint.trim() === '') {
                // 如果选择了日志系统但未填写入口地址，也清空
                payload.log_endpoint = undefined;
                payload.log_auth_type = 'none';
                payload.log_username = undefined;
                payload.log_password = undefined;
            }
            else if (payload.log_auth_type === 'basic') {
                if (!payload.log_username) {
                    throw new Error('LOG_BASIC_REQUIRED');
                }
                if (!payload.log_password) {
                    if (!isEditing) {
                        throw new Error('LOG_BASIC_REQUIRED');
                    }
                    payload.log_password = undefined;
                }
            }
            else if (payload.log_auth_type === 'token') {
                if (!payload.log_password) {
                    if (!isEditing) {
                        throw new Error('LOG_TOKEN_REQUIRED');
                    }
                    payload.log_password = undefined;
                }
                payload.log_username = undefined;
            }
            else {
                payload.log_username = undefined;
                payload.log_password = undefined;
            }
            // 处理证书字段：如果为空则设为 undefined（编辑时留空表示不更新）
            if (!payload.client_cert) {
                payload.client_cert = undefined;
            }
            if (!payload.client_key) {
                payload.client_key = undefined;
            }
            if (!payload.ca_cert) {
                payload.ca_cert = undefined;
            }
            return payload;
        };
        var submitClusterForm = function () { return __awaiter(_this, void 0, void 0, function () {
            var payload, error_2, code, errorMsg, firstError, field;
            var _a, _b, _c;
            return __generator(this, function (_d) {
                switch (_d.label) {
                    case 0: return [4 /*yield*/, ((_a = clusterFormRef.value) === null || _a === void 0 ? void 0 : _a.validate())];
                    case 1:
                        _d.sent();
                        _d.label = 2;
                    case 2:
                        _d.trys.push([2, 7, , 8]);
                        payload = buildClusterPayload(clusterDialog.editing);
                        if (!clusterDialog.editing) return [3 /*break*/, 4];
                        return [4 /*yield*/, (0, observability_1.updateCluster)(clusterDialog.form.id, payload)];
                    case 3:
                        _d.sent();
                        element_plus_1.ElMessage.success('更新成功');
                        return [3 /*break*/, 6];
                    case 4: return [4 /*yield*/, (0, observability_1.createCluster)(payload)];
                    case 5:
                        _d.sent();
                        element_plus_1.ElMessage.success('创建成功');
                        _d.label = 6;
                    case 6:
                        clusterDialog.visible = false;
                        loadClusters();
                        return [3 /*break*/, 8];
                    case 7:
                        error_2 = _d.sent();
                        code = error_2 === null || error_2 === void 0 ? void 0 : error_2.message;
                        if (code === 'PROM_BASIC_REQUIRED') {
                            element_plus_1.ElMessage.warning('Prometheus Basic 认证需要填写用户名和密码');
                        }
                        else if (code === 'PROM_TOKEN_REQUIRED') {
                            element_plus_1.ElMessage.warning('请填写 Prometheus Token');
                        }
                        else if (code === 'LOG_BASIC_REQUIRED') {
                            element_plus_1.ElMessage.warning('日志系统 Basic 认证需要填写用户名和密码');
                        }
                        else if (code === 'LOG_TOKEN_REQUIRED') {
                            element_plus_1.ElMessage.warning('请填写日志系统 Token');
                        }
                        else if (code === 'KUBECONFIG_REQUIRED') {
                            element_plus_1.ElMessage.warning('请上传 kubeconfig 凭证');
                        }
                        else if (!isAuthError(error_2)) {
                            errorMsg = ((_c = (_b = error_2 === null || error_2 === void 0 ? void 0 : error_2.response) === null || _b === void 0 ? void 0 : _b.data) === null || _c === void 0 ? void 0 : _c.detail) || (error_2 === null || error_2 === void 0 ? void 0 : error_2.message) || '保存失败';
                            if (typeof errorMsg === 'string') {
                                element_plus_1.ElMessage.error("\u4FDD\u5B58\u5931\u8D25: ".concat(errorMsg));
                            }
                            else if (Array.isArray(errorMsg)) {
                                firstError = errorMsg[0];
                                if ((firstError === null || firstError === void 0 ? void 0 : firstError.loc) && (firstError === null || firstError === void 0 ? void 0 : firstError.msg)) {
                                    field = firstError.loc.join('.');
                                    element_plus_1.ElMessage.error("\u4FDD\u5B58\u5931\u8D25: ".concat(field, " - ").concat(firstError.msg));
                                }
                                else {
                                    element_plus_1.ElMessage.error("\u4FDD\u5B58\u5931\u8D25: ".concat(JSON.stringify(errorMsg)));
                                }
                            }
                            else {
                                element_plus_1.ElMessage.error('保存失败');
                            }
                        }
                        return [3 /*break*/, 8];
                    case 8: return [2 /*return*/];
                }
            });
        }); };
        var handleDeleteCluster = function (record) { return __awaiter(_this, void 0, void 0, function () {
            var error_3;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 3, , 4]);
                        return [4 /*yield*/, element_plus_1.ElMessageBox.confirm("\u786E\u8BA4\u5220\u9664\u96C6\u7FA4\u3010".concat(record.name, "\u3011\u5417\uFF1F"), '提示', {
                                confirmButtonText: '删除',
                                cancelButtonText: '取消',
                                type: 'warning'
                            })];
                    case 1:
                        _a.sent();
                        return [4 /*yield*/, (0, observability_1.deleteCluster)(record.id)];
                    case 2:
                        _a.sent();
                        element_plus_1.ElMessage.success('删除成功');
                        loadClusters();
                        return [3 /*break*/, 4];
                    case 3:
                        error_3 = _a.sent();
                        // ignore cancel
                        if (!isAuthError(error_3)) {
                            element_plus_1.ElMessage.error('删除失败');
                        }
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        }); };
        var connectivityDialog = (0, vue_1.reactive)({
            visible: false,
            result: null
        });
        var handleTestConnectivity = function (record) { return __awaiter(_this, void 0, void 0, function () {
            var res, error_4;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 2, , 3]);
                        return [4 /*yield*/, (0, observability_1.testClusterConnectivity)(record.id)];
                    case 1:
                        res = _a.sent();
                        connectivityDialog.result = res.data;
                        connectivityDialog.visible = true;
                        return [3 /*break*/, 3];
                    case 2:
                        error_4 = _a.sent();
                        if (!isAuthError(error_4)) {
                            element_plus_1.ElMessage.error('连通性测试失败');
                        }
                        return [3 /*break*/, 3];
                    case 3: return [2 /*return*/];
                }
            });
        }); };
        var handleHealthCheck = function (record) { return __awaiter(_this, void 0, void 0, function () {
            var error_5;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 2, , 3]);
                        return [4 /*yield*/, (0, observability_1.runClusterHealthCheck)(record.id)];
                    case 1:
                        _a.sent();
                        element_plus_1.ElNotification.success({
                            title: '健康检查',
                            message: '健康检查任务已触发'
                        });
                        loadClusters();
                        return [3 /*break*/, 3];
                    case 2:
                        error_5 = _a.sent();
                        if (!isAuthError(error_5)) {
                            element_plus_1.ElMessage.error('健康检查触发失败');
                        }
                        return [3 /*break*/, 3];
                    case 3: return [2 /*return*/];
                }
            });
        }); };
        // 资源快照
        var resourceTypeOptions = [
            { label: 'Pods', value: 'pods' },
            { label: 'Deployments', value: 'deployments' },
            { label: 'StatefulSets', value: 'statefulsets' },
            { label: 'DaemonSets', value: 'daemonsets' },
            { label: 'Jobs', value: 'jobs' },
            { label: 'CronJobs', value: 'cronjobs' },
            { label: 'Services', value: 'services' },
            { label: 'ConfigMaps', value: 'configmaps' },
            { label: 'Events', value: 'events' },
            { label: 'Nodes', value: 'nodes' }
        ];
        var resourceFilters = (0, vue_1.reactive)({
            clusterId: 0,
            resourceType: 'pods',
            namespace: '',
            page: 1,
            size: 10
        });
        var resourcePagination = (0, vue_1.reactive)({
            total: 0
        });
        var resourceSnapshots = (0, vue_1.ref)([]);
        var resourceLoading = (0, vue_1.ref)(false);
        var recentSyncEvents = (0, vue_1.ref)([]);
        var loadResources = function () {
            var args_1 = [];
            for (var _i = 0; _i < arguments.length; _i++) {
                args_1[_i] = arguments[_i];
            }
            return __awaiter(_this, __spreadArray([], args_1, true), void 0, function (resetPage) {
                var res, data, error_6;
                var _a, _b;
                if (resetPage === void 0) { resetPage = false; }
                return __generator(this, function (_c) {
                    switch (_c.label) {
                        case 0:
                            if (!resourceFilters.clusterId)
                                return [2 /*return*/];
                            if (resetPage) {
                                resourceFilters.page = 1;
                            }
                            resourceLoading.value = true;
                            _c.label = 1;
                        case 1:
                            _c.trys.push([1, 3, 4, 5]);
                            return [4 /*yield*/, (0, observability_1.fetchResourceSnapshots)(resourceFilters.clusterId, {
                                    page: resourceFilters.page,
                                    size: resourceFilters.size,
                                    resource_type: resourceFilters.resourceType || undefined,
                                    namespace: resourceFilters.namespace || undefined
                                })];
                        case 2:
                            res = _c.sent();
                            data = res.data || {};
                            resourceSnapshots.value = (_a = data.list) !== null && _a !== void 0 ? _a : [];
                            resourcePagination.total = (_b = data.total) !== null && _b !== void 0 ? _b : 0;
                            return [3 /*break*/, 5];
                        case 3:
                            error_6 = _c.sent();
                            if (!isAuthError(error_6)) {
                                element_plus_1.ElMessage.error('加载资源快照失败');
                            }
                            else {
                                resourceSnapshots.value = [];
                                resourcePagination.total = 0;
                            }
                            return [3 /*break*/, 5];
                        case 4:
                            resourceLoading.value = false;
                            return [7 /*endfinally*/];
                        case 5: return [2 /*return*/];
                    }
                });
            });
        };
        var handleResourcePageChange = function (page) {
            resourceFilters.page = page;
            loadResources();
        };
        var handleManualSync = function () { return __awaiter(_this, void 0, void 0, function () {
            var res, data, syncResult, error_7;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (!resourceFilters.clusterId) {
                            element_plus_1.ElMessage.warning('请先选择集群');
                            return [2 /*return*/];
                        }
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, (0, observability_1.syncClusterResources)(resourceFilters.clusterId, {
                                namespace: resourceFilters.namespace || undefined,
                                resource_types: [resourceFilters.resourceType],
                                limit: resourceFilters.size
                            })];
                    case 2:
                        res = _b.sent();
                        data = res.data || {};
                        syncResult = data[resourceFilters.resourceType];
                        if (syncResult === null || syncResult === void 0 ? void 0 : syncResult.events) {
                            recentSyncEvents.value = syncResult.events.map(function (item) { return ({
                                timestamp: (0, format_1.formatDateTime)(new Date().toISOString()),
                                type: item.type,
                                message: "\u8D44\u6E90 ".concat(item.uid, " ").concat(item.type),
                                diff: item.diff,
                                uid: item.uid
                            }); });
                        }
                        element_plus_1.ElMessage.success("\u540C\u6B65\u5B8C\u6210\uFF0C\u53D8\u66F4 ".concat(((_a = syncResult === null || syncResult === void 0 ? void 0 : syncResult.events) === null || _a === void 0 ? void 0 : _a.length) || 0, " \u6761"));
                        loadResources();
                        return [3 /*break*/, 4];
                    case 3:
                        error_7 = _b.sent();
                        if (!isAuthError(error_7)) {
                            element_plus_1.ElMessage.error('同步失败');
                        }
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        }); };
        // 指标分析
        var metricTemplateOptions = [
            { label: 'Pod CPU 使用率', value: 'pod_cpu_usage' },
            { label: 'Pod 内存使用', value: 'pod_memory_usage' },
            { label: 'Pod 重启速率', value: 'pod_restart_rate' },
            { label: 'Node CPU 总量', value: 'node_cpu_total' },
            { label: 'Node 内存使用', value: 'node_memory_usage' }
        ];
        var defaultTimeRange = [
            new Date(Date.now() - 30 * 60 * 1000),
            new Date()
        ];
        var metricsForm = (0, vue_1.reactive)({
            cluster_id: 0,
            template_id: 'pod_cpu_usage',
            promql: '',
            range: defaultTimeRange,
            step_seconds: 60,
            context: {
                namespace: '',
                pod: '',
                window: '5m'
            }
        });
        var metricsResult = (0, vue_1.ref)(null);
        // 命名空间和 Pod 列表
        var namespaces = (0, vue_1.ref)([]);
        var pods = (0, vue_1.ref)([]);
        var namespaceLoading = (0, vue_1.ref)(false);
        var podLoading = (0, vue_1.ref)(false);
        // 加载命名空间列表
        var loadNamespaces = function (clusterId) { return __awaiter(_this, void 0, void 0, function () {
            var res, error_8;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!clusterId) {
                            namespaces.value = [];
                            metricsForm.context.namespace = '';
                            return [2 /*return*/];
                        }
                        namespaceLoading.value = true;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, (0, observability_1.fetchClusterNamespaces)(clusterId)];
                    case 2:
                        res = _a.sent();
                        namespaces.value = res.data || [];
                        // 如果当前命名空间不在列表中，清空
                        if (metricsForm.context.namespace && !namespaces.value.includes(metricsForm.context.namespace)) {
                            metricsForm.context.namespace = '';
                            metricsForm.context.pod = '';
                            pods.value = [];
                        }
                        return [3 /*break*/, 5];
                    case 3:
                        error_8 = _a.sent();
                        if (!isAuthError(error_8)) {
                            element_plus_1.ElMessage.error('加载命名空间列表失败');
                        }
                        namespaces.value = [];
                        return [3 /*break*/, 5];
                    case 4:
                        namespaceLoading.value = false;
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        }); };
        // 加载 Pod 列表
        var loadPods = function (clusterId, namespace) { return __awaiter(_this, void 0, void 0, function () {
            var res, error_9;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!clusterId || !namespace) {
                            pods.value = [];
                            metricsForm.context.pod = '';
                            return [2 /*return*/];
                        }
                        podLoading.value = true;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, (0, observability_1.fetchClusterPods)(clusterId, namespace)];
                    case 2:
                        res = _a.sent();
                        pods.value = res.data || [];
                        // 如果当前 Pod 不在列表中，清空
                        if (metricsForm.context.pod && !pods.value.includes(metricsForm.context.pod)) {
                            metricsForm.context.pod = '';
                        }
                        return [3 /*break*/, 5];
                    case 3:
                        error_9 = _a.sent();
                        if (!isAuthError(error_9)) {
                            element_plus_1.ElMessage.error('加载Pod列表失败');
                        }
                        pods.value = [];
                        return [3 /*break*/, 5];
                    case 4:
                        podLoading.value = false;
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        }); };
        // 监听集群变化，加载命名空间列表
        (0, vue_1.watch)(function () { return metricsForm.cluster_id; }, function (clusterId) {
            loadNamespaces(clusterId);
            metricsForm.context.namespace = '';
            metricsForm.context.pod = '';
            pods.value = [];
        });
        // 命名空间变化时，加载 Pod 列表
        var handleNamespaceChange = function (namespace) {
            metricsForm.context.pod = '';
            loadPods(metricsForm.cluster_id, namespace);
        };
        // 根据模板判断需要哪些参数
        var needsNamespace = (0, vue_1.computed)(function () {
            var podTemplates = ['pod_cpu_usage', 'pod_memory_usage', 'pod_restart_rate'];
            return metricsForm.template_id && podTemplates.includes(metricsForm.template_id);
        });
        var needsPod = (0, vue_1.computed)(function () {
            var podTemplates = ['pod_cpu_usage', 'pod_memory_usage', 'pod_restart_rate'];
            return metricsForm.template_id && podTemplates.includes(metricsForm.template_id);
        });
        var needsWindow = (0, vue_1.computed)(function () {
            var windowTemplates = ['pod_cpu_usage', 'pod_restart_rate', 'node_cpu_total'];
            return metricsForm.template_id && windowTemplates.includes(metricsForm.template_id);
        });
        var handleTemplateChange = function () {
            // 切换模板时，重置 context 中的默认值
            if (!needsNamespace.value) {
                metricsForm.context.namespace = '';
                metricsForm.context.pod = '';
                pods.value = [];
            }
            else if (metricsForm.cluster_id && !metricsForm.context.namespace) {
                // 如果需要命名空间但没有选择，重新加载命名空间列表
                loadNamespaces(metricsForm.cluster_id);
            }
            if (!needsPod.value) {
                metricsForm.context.pod = '';
            }
            if (!needsWindow.value) {
                metricsForm.context.window = '';
            }
            else if (!metricsForm.context.window) {
                metricsForm.context.window = '5m';
            }
        };
        var handleQueryMetrics = function () { return __awaiter(_this, void 0, void 0, function () {
            var payload, context, res, error_10;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!metricsForm.cluster_id) {
                            element_plus_1.ElMessage.warning('请选择集群');
                            return [2 /*return*/];
                        }
                        if (!metricsForm.template_id && !metricsForm.promql) {
                            element_plus_1.ElMessage.warning('请选择模板或填写 PromQL');
                            return [2 /*return*/];
                        }
                        // 验证模板所需的参数
                        if (metricsForm.template_id && !metricsForm.promql) {
                            if (needsNamespace.value && !metricsForm.context.namespace) {
                                element_plus_1.ElMessage.warning('请填写命名空间');
                                return [2 /*return*/];
                            }
                            if (needsPod.value && !metricsForm.context.pod) {
                                element_plus_1.ElMessage.warning('请填写Pod名称');
                                return [2 /*return*/];
                            }
                            if (needsWindow.value && !metricsForm.context.window) {
                                element_plus_1.ElMessage.warning('请填写时间窗口（如: 5m）');
                                return [2 /*return*/];
                            }
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        payload = {
                            cluster_id: metricsForm.cluster_id,
                            template_id: metricsForm.template_id || undefined,
                            promql: metricsForm.promql || undefined,
                            step_seconds: metricsForm.step_seconds || undefined
                        };
                        if (metricsForm.range && metricsForm.range.length === 2) {
                            payload.start = metricsForm.range[0].toISOString();
                            payload.end = metricsForm.range[1].toISOString();
                        }
                        // 如果使用模板，需要传递 context 参数
                        if (metricsForm.template_id && !metricsForm.promql) {
                            context = {};
                            if (needsNamespace.value && metricsForm.context.namespace) {
                                context.namespace = metricsForm.context.namespace;
                            }
                            if (needsPod.value && metricsForm.context.pod) {
                                context.pod = metricsForm.context.pod;
                            }
                            if (needsWindow.value && metricsForm.context.window) {
                                context.window = metricsForm.context.window;
                            }
                            if (Object.keys(context).length > 0) {
                                payload.context = context;
                            }
                        }
                        return [4 /*yield*/, (0, observability_1.queryMetrics)(payload)];
                    case 2:
                        res = _a.sent();
                        metricsResult.value = res.data;
                        element_plus_1.ElMessage.success('指标查询成功');
                        return [3 /*break*/, 4];
                    case 3:
                        error_10 = _a.sent();
                        metricsResult.value = null;
                        if (!isAuthError(error_10)) {
                            element_plus_1.ElMessage.error('指标查询失败');
                        }
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        }); };
        var resetMetricsForm = function () {
            metricsForm.template_id = 'pod_cpu_usage';
            metricsForm.promql = '';
            metricsForm.range = __spreadArray([], defaultTimeRange, true);
            metricsForm.step_seconds = 60;
            metricsForm.context = {
                namespace: '',
                pod: '',
                window: '5m'
            };
            metricsResult.value = null;
            // 如果选择了集群，重新加载命名空间列表
            if (metricsForm.cluster_id) {
                loadNamespaces(metricsForm.cluster_id);
            }
        };
        var metricsSeries = (0, vue_1.computed)(function () {
            var _a, _b;
            if (!((_a = metricsResult.value) === null || _a === void 0 ? void 0 : _a.data))
                return [];
            var result = ((_b = metricsResult.value.data) === null || _b === void 0 ? void 0 : _b.result) || [];
            return result.map(function (item) {
                var labels = item.metric || {};
                var values = item.values || (item.value ? [item.value] : []);
                var numeric = values
                    .map(function (v) { return parseFloat(v[1]); })
                    .filter(function (num) { return !Number.isNaN(num); });
                var latest = numeric.length ? numeric[numeric.length - 1] : null;
                var average = numeric.length > 0
                    ? Number((numeric.reduce(function (sum, num) { return sum + num; }, 0) / numeric.length).toFixed(4))
                    : null;
                return {
                    series: Object.entries(labels)
                        .map(function (_a) {
                        var key = _a[0], value = _a[1];
                        return "".concat(key, "=").concat(value);
                    })
                        .join(', '),
                    labels: labels,
                    latest: latest,
                    average: average
                };
            });
        });
        // 图表配置
        var chartOptions = (0, vue_1.computed)(function () {
            var _a, _b;
            if (!((_a = metricsResult.value) === null || _a === void 0 ? void 0 : _a.data))
                return null;
            var result = ((_b = metricsResult.value.data) === null || _b === void 0 ? void 0 : _b.result) || [];
            if (result.length === 0)
                return null;
            // 处理时间序列数据
            var series = [];
            var xAxisData = [];
            var allTimes = new Set();
            // 收集所有时间点
            result.forEach(function (item) {
                var values = item.values || (item.value ? [item.value] : []);
                values.forEach(function (v) {
                    allTimes.add(v[0]);
                });
            });
            // 排序时间点
            var sortedTimes = Array.from(allTimes).sort(function (a, b) { return a - b; });
            // 构建 x 轴数据
            xAxisData.push.apply(xAxisData, sortedTimes.map(function (t) {
                var date = new Date(t * 1000);
                return date.toLocaleString('zh-CN', {
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                });
            }));
            // 为每个时间序列创建系列
            result.forEach(function (item, index) {
                var labels = item.metric || {};
                var values = item.values || (item.value ? [item.value] : []);
                // 创建时间到值的映射
                var valueMap = new Map();
                values.forEach(function (v) {
                    valueMap.set(v[0], parseFloat(v[1]));
                });
                // 构建数据点（如果没有对应时间点的值，使用 null）
                var data = sortedTimes.map(function (time) {
                    var value = valueMap.get(time);
                    return value !== undefined ? value : null;
                });
                // 生成系列名称
                var seriesName = Object.keys(labels).length > 0
                    ? Object.entries(labels)
                        .map(function (_a) {
                        var key = _a[0], value = _a[1];
                        return "".concat(key, "=").concat(value);
                    })
                        .join(', ')
                    : "Series ".concat(index + 1);
                series.push({
                    name: seriesName,
                    type: 'line',
                    data: data,
                    smooth: true,
                    symbol: 'circle',
                    symbolSize: 4,
                    lineStyle: {
                        width: 2
                    }
                });
            });
            return {
                title: {
                    text: '指标趋势',
                    left: 'center',
                    textStyle: {
                        color: '#fff'
                    }
                },
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'cross'
                    },
                    formatter: function (params) {
                        var result = "<div style=\"margin-bottom: 4px;\">".concat(params[0].axisValue, "</div>");
                        params.forEach(function (param) {
                            var value = param.value !== null ? param.value.toFixed(4) : 'N/A';
                            result += "<div style=\"margin-top: 4px;\">\n                <span style=\"display:inline-block;width:10px;height:10px;border-radius:50%;background-color:".concat(param.color, ";margin-right:5px;\"></span>\n                ").concat(param.seriesName, ": <strong>").concat(value, "</strong>\n              </div>");
                        });
                        return result;
                    }
                },
                legend: {
                    data: series.map(function (s) { return s.name; }),
                    top: 30,
                    textStyle: {
                        color: '#fff'
                    }
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '10%',
                    top: '15%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    boundaryGap: false,
                    data: xAxisData,
                    axisLabel: {
                        color: '#999',
                        rotate: 45
                    },
                    axisLine: {
                        lineStyle: {
                            color: '#666'
                        }
                    }
                },
                yAxis: {
                    type: 'value',
                    axisLabel: {
                        color: '#999'
                    },
                    axisLine: {
                        lineStyle: {
                            color: '#666'
                        }
                    },
                    splitLine: {
                        lineStyle: {
                            color: '#333',
                            type: 'dashed'
                        }
                    }
                },
                dataZoom: [
                    {
                        type: 'slider',
                        show: true,
                        xAxisIndex: [0],
                        start: 0,
                        end: 100,
                        bottom: 20,
                        textStyle: {
                            color: '#999'
                        }
                    },
                    {
                        type: 'inside',
                        xAxisIndex: [0],
                        start: 0,
                        end: 100
                    }
                ],
                series: series
            };
        });
        // 日志检索
        var logForm = (0, vue_1.reactive)({
            cluster_id: 0,
            query: '',
            range: defaultTimeRange,
            limit: 100,
            page: 1,
            page_size: 100,
            highlight: true,
            stats: true
        });
        var logResult = (0, vue_1.ref)(null);
        var handleQueryLogs = function () { return __awaiter(_this, void 0, void 0, function () {
            var payload, res, error_11;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!logForm.cluster_id) {
                            element_plus_1.ElMessage.warning('请选择集群');
                            return [2 /*return*/];
                        }
                        if (!logForm.query) {
                            element_plus_1.ElMessage.warning('请输入查询语句');
                            return [2 /*return*/];
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        payload = {
                            cluster_id: logForm.cluster_id,
                            query: logForm.query,
                            limit: logForm.limit,
                            page: logForm.page,
                            page_size: logForm.page_size,
                            highlight: logForm.highlight,
                            stats: logForm.stats
                        };
                        if (logForm.range && logForm.range.length === 2) {
                            payload.start = logForm.range[0].toISOString();
                            payload.end = logForm.range[1].toISOString();
                        }
                        return [4 /*yield*/, (0, observability_1.queryLogs)(payload)];
                    case 2:
                        res = _a.sent();
                        logResult.value = res.data;
                        element_plus_1.ElMessage.success('日志查询成功');
                        return [3 /*break*/, 4];
                    case 3:
                        error_11 = _a.sent();
                        logResult.value = null;
                        if (!isAuthError(error_11)) {
                            element_plus_1.ElMessage.error('日志查询失败');
                        }
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        }); };
        var resetLogForm = function () {
            logForm.query = '';
            logForm.page = 1;
            logResult.value = null;
        };
        // 诊断记录
        var diagnosisPagination = (0, vue_1.reactive)({
            page: 1,
            size: 10,
            total: 0
        });
        var diagnosisList = (0, vue_1.ref)([]);
        var diagnosisLoading = (0, vue_1.ref)(false);
        // 诊断状态轮询
        var diagnosisPollTimer = null;
        var DIAGNOSIS_POLL_INTERVAL = 3000; // 3秒轮询一次
        var startDiagnosisPolling = function () {
            // 如果已经有定时器在运行，先清除
            if (diagnosisPollTimer) {
                clearInterval(diagnosisPollTimer);
            }
            // 启动轮询
            diagnosisPollTimer = window.setInterval(function () {
                // 检查是否有正在进行的诊断任务
                var hasRunningDiagnosis = diagnosisList.value.some(function (record) { var _a; return ['pending', 'running', 'pending_next'].includes(((_a = record.status) === null || _a === void 0 ? void 0 : _a.toLowerCase()) || ''); });
                if (hasRunningDiagnosis && activeTab.value === 'diagnosis') {
                    // 静默刷新，不显示loading
                    loadDiagnosis().catch(function () {
                        // 静默失败
                    });
                }
                else {
                    // 没有进行中的诊断，停止轮询
                    stopDiagnosisPolling();
                }
            }, DIAGNOSIS_POLL_INTERVAL);
        };
        var stopDiagnosisPolling = function () {
            if (diagnosisPollTimer) {
                clearInterval(diagnosisPollTimer);
                diagnosisPollTimer = null;
            }
        };
        var loadDiagnosis = function () { return __awaiter(_this, void 0, void 0, function () {
            var res, data, error_12;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        diagnosisLoading.value = true;
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, (0, observability_1.listDiagnosisRecords)({
                                page: diagnosisPagination.page,
                                size: diagnosisPagination.size
                            })];
                    case 2:
                        res = _c.sent();
                        data = res.data || {};
                        diagnosisList.value = (_a = data.list) !== null && _a !== void 0 ? _a : [];
                        diagnosisPagination.total = (_b = data.total) !== null && _b !== void 0 ? _b : 0;
                        return [3 /*break*/, 5];
                    case 3:
                        error_12 = _c.sent();
                        diagnosisList.value = [];
                        diagnosisPagination.total = 0;
                        return [3 /*break*/, 5];
                    case 4:
                        diagnosisLoading.value = false;
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        }); };
        var createDiagnosisForm = function () { return ({
            cluster_id: 0,
            namespace: '',
            resource_type: 'pods',
            resource_name: '',
            time_range_hours: 2.0
        }); };
        var diagnosisDialog = (0, vue_1.reactive)({
            visible: false,
            submitting: false,
            form: createDiagnosisForm()
        });
        var diagnosisNamespaces = (0, vue_1.ref)([]);
        var diagnosisResources = (0, vue_1.ref)([]);
        var diagnosisNamespaceLoading = (0, vue_1.ref)(false);
        var diagnosisResourceLoading = (0, vue_1.ref)(false);
        var ensureClusterSelection = function () {
            if (!clusters.value.length)
                return;
            var exists = clusters.value.some(function (cluster) { return cluster.id === diagnosisDialog.form.cluster_id; });
            if (!exists) {
                diagnosisDialog.form.cluster_id = clusters.value[0].id;
            }
        };
        var refreshDiagnosisOptions = function () { return __awaiter(_this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, loadDiagnosisNamespaces()];
                    case 1:
                        _a.sent();
                        return [4 /*yield*/, loadDiagnosisResources()];
                    case 2:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        }); };
        var openManualDiagnosis = function () { return __awaiter(_this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!!clusters.value.length) return [3 /*break*/, 2];
                        return [4 /*yield*/, loadClusters()];
                    case 1:
                        _a.sent();
                        _a.label = 2;
                    case 2:
                        if (!clusters.value.length) {
                            element_plus_1.ElMessage.warning('请先添加集群配置');
                            return [2 /*return*/];
                        }
                        ensureClusterSelection();
                        diagnosisDialog.form.resource_name = '';
                        diagnosisDialog.visible = true;
                        return [4 /*yield*/, (0, vue_1.nextTick)()];
                    case 3:
                        _a.sent();
                        return [4 /*yield*/, refreshDiagnosisOptions()];
                    case 4:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        }); };
        var loadDiagnosisNamespaces = function () { return __awaiter(_this, void 0, void 0, function () {
            var clusterId, res, list, error_13;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        clusterId = diagnosisDialog.form.cluster_id;
                        if (!clusterId) {
                            diagnosisNamespaces.value = [];
                            diagnosisDialog.form.namespace = '';
                            return [2 /*return*/];
                        }
                        diagnosisNamespaceLoading.value = true;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, (0, observability_1.fetchClusterNamespaces)(clusterId)];
                    case 2:
                        res = _a.sent();
                        list = Array.isArray(res === null || res === void 0 ? void 0 : res.data) ? res.data : [];
                        diagnosisNamespaces.value = __spreadArray([], list, true);
                        if (!list.length) {
                            diagnosisDialog.form.namespace = '';
                        }
                        else if (!diagnosisDialog.form.namespace || !list.includes(diagnosisDialog.form.namespace)) {
                            diagnosisDialog.form.namespace = list.includes('default') ? 'default' : list[0];
                        }
                        return [3 /*break*/, 5];
                    case 3:
                        error_13 = _a.sent();
                        console.error('[ERROR] loadDiagnosisNamespaces failed:', error_13);
                        diagnosisNamespaces.value = [];
                        diagnosisDialog.form.namespace = '';
                        if (!isAuthError(error_13)) {
                            element_plus_1.ElMessage.error('加载命名空间失败');
                        }
                        return [3 /*break*/, 5];
                    case 4:
                        diagnosisNamespaceLoading.value = false;
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        }); };
        var loadDiagnosisResources = function () { return __awaiter(_this, void 0, void 0, function () {
            var clusterId, resourceType, params, res, list, resData, names, error_14;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        clusterId = diagnosisDialog.form.cluster_id;
                        resourceType = diagnosisDialog.form.resource_type;
                        if (!clusterId || !resourceType) {
                            diagnosisResources.value = [];
                            diagnosisDialog.form.resource_name = '';
                            return [2 /*return*/];
                        }
                        if (resourceType !== 'nodes' && !diagnosisDialog.form.namespace) {
                            diagnosisResources.value = [];
                            diagnosisDialog.form.resource_name = '';
                            return [2 /*return*/];
                        }
                        diagnosisResourceLoading.value = true;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        params = {
                            page: 1,
                            size: 200,
                            resource_type: resourceType
                        };
                        if (diagnosisDialog.form.namespace) {
                            params.namespace = diagnosisDialog.form.namespace;
                        }
                        return [4 /*yield*/, (0, observability_1.fetchResourceSnapshots)(clusterId, params)];
                    case 2:
                        res = _a.sent();
                        list = [];
                        if (res === null || res === void 0 ? void 0 : res.data) {
                            resData = res.data;
                            if (typeof resData === 'object' && !Array.isArray(resData)) {
                                if (Array.isArray(resData.list)) {
                                    list = resData.list;
                                }
                                else if (resData.list && Array.isArray(resData.list)) {
                                    list = resData.list;
                                }
                            }
                            else if (Array.isArray(resData)) {
                                list = resData;
                            }
                        }
                        names = Array.from(new Set(list.map(function (item) { return item.resource_name; }).filter(Boolean)));
                        diagnosisResources.value = __spreadArray([], names, true);
                        if (diagnosisDialog.form.resource_name && !names.includes(diagnosisDialog.form.resource_name)) {
                            diagnosisDialog.form.resource_name = names[0] || '';
                        }
                        else if (!diagnosisDialog.form.resource_name && names.length > 0) {
                            diagnosisDialog.form.resource_name = names[0];
                        }
                        return [3 /*break*/, 5];
                    case 3:
                        error_14 = _a.sent();
                        console.error('[ERROR] loadDiagnosisResources failed:', error_14);
                        diagnosisResources.value = [];
                        diagnosisDialog.form.resource_name = '';
                        if (!isAuthError(error_14)) {
                            element_plus_1.ElMessage.error('加载资源列表失败');
                        }
                        return [3 /*break*/, 5];
                    case 4:
                        diagnosisResourceLoading.value = false;
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        }); };
        var submitManualDiagnosis = function () { return __awaiter(_this, void 0, void 0, function () {
            var error_15;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!diagnosisDialog.form.cluster_id) {
                            element_plus_1.ElMessage.warning('请选择集群');
                            return [2 /*return*/];
                        }
                        if (diagnosisDialog.form.resource_type !== 'nodes' && !diagnosisDialog.form.namespace) {
                            element_plus_1.ElMessage.warning('请选择命名空间');
                            return [2 /*return*/];
                        }
                        if (!diagnosisDialog.form.resource_name) {
                            element_plus_1.ElMessage.warning('请选择资源');
                            return [2 /*return*/];
                        }
                        diagnosisDialog.submitting = true;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 6, 7, 8]);
                        return [4 /*yield*/, (0, observability_1.runDiagnosis)({
                                cluster_id: diagnosisDialog.form.cluster_id,
                                namespace: diagnosisDialog.form.namespace || undefined,
                                resource_type: diagnosisDialog.form.resource_type,
                                resource_name: diagnosisDialog.form.resource_name,
                                time_range_hours: diagnosisDialog.form.time_range_hours || 2.0
                            })];
                    case 2:
                        _a.sent();
                        diagnosisDialog.visible = false;
                        element_plus_1.ElMessage.success('诊断任务已触发，正在后台执行');
                        if (!(activeTab.value !== 'diagnosis')) return [3 /*break*/, 4];
                        activeTab.value = 'diagnosis';
                        return [4 /*yield*/, (0, vue_1.nextTick)()];
                    case 3:
                        _a.sent();
                        _a.label = 4;
                    case 4: return [4 /*yield*/, loadDiagnosis()];
                    case 5:
                        _a.sent();
                        startDiagnosisPolling();
                        (0, element_plus_1.ElNotification)({
                            title: '诊断已启动',
                            message: "".concat(diagnosisDialog.form.namespace || 'default', "/").concat(diagnosisDialog.form.resource_name, " \u7684\u8BCA\u65AD\u4EFB\u52A1\u5DF2\u5F00\u59CB\u6267\u884C"),
                            type: 'info',
                            duration: 5000
                        });
                        return [3 /*break*/, 8];
                    case 6:
                        error_15 = _a.sent();
                        if (!isAuthError(error_15)) {
                            element_plus_1.ElMessage.error('诊断触发失败');
                        }
                        return [3 /*break*/, 8];
                    case 7:
                        diagnosisDialog.submitting = false;
                        return [7 /*endfinally*/];
                    case 8: return [2 /*return*/];
                }
            });
        }); };
        var handleDiagnosisClusterChange = function (value) { return __awaiter(_this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        diagnosisDialog.form.cluster_id = value;
                        diagnosisDialog.form.namespace = '';
                        diagnosisDialog.form.resource_name = '';
                        return [4 /*yield*/, refreshDiagnosisOptions()];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        }); };
        var handleDiagnosisNamespaceChange = function (value) { return __awaiter(_this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        diagnosisDialog.form.namespace = value || '';
                        diagnosisDialog.form.resource_name = '';
                        return [4 /*yield*/, loadDiagnosisResources()];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        }); };
        var handleDiagnosisResourceTypeChange = function (value) { return __awaiter(_this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        diagnosisDialog.form.resource_type = value || 'pods';
                        diagnosisDialog.form.resource_name = '';
                        return [4 /*yield*/, loadDiagnosisResources()];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        }); };
        (0, vue_1.watch)(function () { return diagnosisDialog.visible; }, function (visible) {
            if (!visible) {
                diagnosisDialog.submitting = false;
                diagnosisNamespaces.value = [];
                diagnosisResources.value = [];
                Object.assign(diagnosisDialog.form, createDiagnosisForm());
            }
        });
        var diagnosisDrawer = (0, vue_1.reactive)({
            visible: false,
            record: null
        });
        var diagnosisUpdatedAt = (0, vue_1.computed)(function () {
            if (!diagnosisDrawer.record)
                return '';
            var timestamp = diagnosisDrawer.record.updated_at || diagnosisDrawer.record.created_at;
            return timestamp ? (0, format_1.formatDateTime)(timestamp) : '';
        });
        var diagnosisConfidencePercent = (0, vue_1.computed)(function () {
            if (!diagnosisDrawer.record || diagnosisDrawer.record.confidence == null)
                return null;
            return Math.round((diagnosisDrawer.record.confidence || 0) * 100);
        });
        var diagnosisConfidenceStatus = (0, vue_1.computed)(function () {
            if (!diagnosisDrawer.record || diagnosisDrawer.record.confidence == null)
                return 'warning';
            var value = diagnosisDrawer.record.confidence;
            if (value > 0.7)
                return 'success';
            if (value > 0.4)
                return 'warning';
            return 'exception';
        });
        var feedbackForm = (0, vue_1.reactive)({
            feedback_type: 'confirmed',
            feedback_notes: '',
            action_taken: '',
            iteration_no: undefined
        });
        var requiresFeedbackNotes = (0, vue_1.computed)(function () { return feedbackForm.feedback_type === 'continue_investigation' || feedbackForm.feedback_type === 'custom'; });
        var feedbackNotesPlaceholder = (0, vue_1.computed)(function () {
            if (feedbackForm.feedback_type === 'continue_investigation') {
                return '请描述为什么需要继续排查、缺失哪些信息、希望系统补充什么';
            }
            if (feedbackForm.feedback_type === 'custom') {
                return '请输入详细的反馈说明，便于后续跟进';
            }
            return '可选，如：已确认是配置变更导致，可沉淀为知识库案例';
        });
        var getLatestIterationNo = function (iterations) {
            if (!iterations || iterations.length === 0)
                return undefined;
            return iterations[iterations.length - 1].iteration_no;
        };
        var resetFeedbackForm = function (record, fallbackIterations) {
            feedbackForm.feedback_type = 'confirmed';
            feedbackForm.feedback_notes = '';
            feedbackForm.action_taken = '';
            feedbackForm.iteration_no = getLatestIterationNo((record === null || record === void 0 ? void 0 : record.iterations) || fallbackIterations);
        };
        var syncFeedbackIterationSelection = function (iterations) {
            if (!iterations || iterations.length === 0) {
                feedbackForm.iteration_no = undefined;
                return;
            }
            var exists = feedbackForm.iteration_no
                ? iterations.some(function (item) { return item.iteration_no === feedbackForm.iteration_no; })
                : false;
            if (!exists) {
                feedbackForm.iteration_no = iterations[iterations.length - 1].iteration_no;
            }
        };
        var iterationTimeline = (0, vue_1.ref)([]);
        var memoryTimeline = (0, vue_1.ref)([]);
        var iterationLoading = (0, vue_1.ref)(false);
        var memoryLoading = (0, vue_1.ref)(false);
        var diagnosisReport = (0, vue_1.ref)(null);
        var feedbackOptions = FEEDBACK_OPTIONS;
        var iterationOptions = (0, vue_1.computed)(function () {
            var _a;
            var source = iterationTimeline.value.length
                ? iterationTimeline.value
                : ((_a = diagnosisDrawer.record) === null || _a === void 0 ? void 0 : _a.iterations) || [];
            return source.map(function (item) { return ({
                label: "\u7B2C ".concat(item.iteration_no, " \u8F6E"),
                value: item.iteration_no
            }); });
        });
        var feedbackState = (0, vue_1.computed)(function () {
            var _a;
            var feedback = (_a = diagnosisDrawer.record) === null || _a === void 0 ? void 0 : _a.feedback;
            return (feedback === null || feedback === void 0 ? void 0 : feedback.state) || null;
        });
        var feedbackLatest = (0, vue_1.computed)(function () {
            var _a;
            var feedback = (_a = diagnosisDrawer.record) === null || _a === void 0 ? void 0 : _a.feedback;
            return (feedback === null || feedback === void 0 ? void 0 : feedback.latest) || null;
        });
        var formatFeedbackType = function (type) {
            switch (type) {
                case 'confirmed':
                    return '已确认根因';
                case 'continue_investigation':
                    return '继续排查';
                case 'custom':
                    return '其他反馈';
                default:
                    return '未知';
            }
        };
        var feedbackStateDescription = (0, vue_1.computed)(function () {
            var _a, _b, _c, _d;
            if (!feedbackState.value)
                return '';
            var state = feedbackState.value;
            if (state.last_feedback_type === 'continue_investigation') {
                var lastIteration = (_a = state.last_feedback_iteration) !== null && _a !== void 0 ? _a : '-';
                var nextIterationLabel = typeof state.last_feedback_iteration === 'number' && !Number.isNaN(state.last_feedback_iteration)
                    ? "\u7B2C".concat(state.last_feedback_iteration + 1, "\u8F6E")
                    : '下一轮';
                var continueStep = (_b = state.continue_from_step) !== null && _b !== void 0 ? _b : 1;
                var minStep = (_c = state.min_steps_before_exit) !== null && _c !== void 0 ? _c : 3;
                return "\u4E0A\u4E00\u8F6E\uFF08\u7B2C".concat(lastIteration, "\u8F6E\uFF09\u5728\u7B2C ").concat(continueStep, " \u6B65\u7ED3\u675F\u5E76\u8981\u6C42\u7EE7\u7EED\u6392\u67E5\uFF0C\u56E0\u6B64\u672C\u8F6E\uFF08").concat(nextIterationLabel, "\uFF09\u5FC5\u987B\u81F3\u5C11\u6267\u884C\u5230\u7B2C ").concat(minStep, " \u6B65\u540E\u624D\u80FD\u7ED3\u675F\u3002");
            }
            if (state.last_feedback_type === 'confirmed') {
                return "\u4E0A\u4E00\u8F6E\uFF08\u7B2C".concat((_d = state.last_feedback_iteration) !== null && _d !== void 0 ? _d : '-', "\u8F6E\uFF09\u5DF2\u786E\u8BA4\u5F53\u524D\u8BCA\u65AD\u7ED3\u8BBA\u3002");
            }
            return '';
        });
        var loadIterationTimeline = function (recordId) { return __awaiter(_this, void 0, void 0, function () {
            var res, error_16;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        iterationLoading.value = true;
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, (0, observability_1.listDiagnosisIterations)(recordId)];
                    case 2:
                        res = _c.sent();
                        iterationTimeline.value = (_b = (_a = res.data) === null || _a === void 0 ? void 0 : _a.list) !== null && _b !== void 0 ? _b : [];
                        syncFeedbackIterationSelection(iterationTimeline.value);
                        return [3 /*break*/, 5];
                    case 3:
                        error_16 = _c.sent();
                        if (!isAuthError(error_16)) {
                            element_plus_1.ElMessage.error('加载迭代历史失败');
                        }
                        else {
                            iterationTimeline.value = [];
                            syncFeedbackIterationSelection([]);
                        }
                        return [3 /*break*/, 5];
                    case 4:
                        iterationLoading.value = false;
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        }); };
        var loadMemoryTimeline = function (recordId) { return __awaiter(_this, void 0, void 0, function () {
            var res, error_17;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        memoryLoading.value = true;
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, (0, observability_1.listDiagnosisMemories)(recordId)];
                    case 2:
                        res = _c.sent();
                        memoryTimeline.value = (_b = (_a = res.data) === null || _a === void 0 ? void 0 : _a.list) !== null && _b !== void 0 ? _b : [];
                        return [3 /*break*/, 5];
                    case 3:
                        error_17 = _c.sent();
                        if (!isAuthError(error_17)) {
                            element_plus_1.ElMessage.error('加载上下文记忆失败');
                        }
                        else {
                            memoryTimeline.value = [];
                        }
                        return [3 /*break*/, 5];
                    case 4:
                        memoryLoading.value = false;
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        }); };
        var loadDiagnosisReport = function (recordId) { return __awaiter(_this, void 0, void 0, function () {
            var res, error_18;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 2, , 3]);
                        return [4 /*yield*/, (0, observability_1.getDiagnosisReport)(recordId)];
                    case 1:
                        res = _a.sent();
                        diagnosisReport.value = res.data;
                        return [3 /*break*/, 3];
                    case 2:
                        error_18 = _a.sent();
                        if (!isAuthError(error_18)) {
                            // 静默失败，报告可能不存在
                            diagnosisReport.value = null;
                        }
                        return [3 /*break*/, 3];
                    case 3: return [2 /*return*/];
                }
            });
        }); };
        var openDiagnosisDetail = function (record) { return __awaiter(_this, void 0, void 0, function () {
            var targetRecord, res, error_19;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        diagnosisDrawer.visible = true;
                        diagnosisDrawer.record = record;
                        resetFeedbackForm(record);
                        targetRecord = record;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, (0, observability_1.getDiagnosisRecord)(record.id)];
                    case 2:
                        res = _a.sent();
                        diagnosisDrawer.record = res.data;
                        targetRecord = res.data;
                        // 如果 symptoms 是字符串，尝试解析
                        if ((targetRecord === null || targetRecord === void 0 ? void 0 : targetRecord.symptoms) && typeof targetRecord.symptoms === 'string') {
                            try {
                                targetRecord.symptoms = JSON.parse(targetRecord.symptoms);
                                diagnosisDrawer.record = targetRecord;
                            }
                            catch (e) {
                                // 解析失败，保持原样
                            }
                        }
                        return [3 /*break*/, 4];
                    case 3:
                        error_19 = _a.sent();
                        console.error('[ERROR] getDiagnosisRecord failed:', error_19);
                        if (!isAuthError(error_19)) {
                            element_plus_1.ElMessage.error('获取诊断详情失败');
                        }
                        diagnosisDrawer.record = record;
                        targetRecord = record;
                        return [3 /*break*/, 4];
                    case 4:
                        resetFeedbackForm(targetRecord);
                        // 加载迭代历史和记忆
                        if (targetRecord) {
                            loadIterationTimeline(targetRecord.id);
                            loadMemoryTimeline(targetRecord.id);
                            if (targetRecord.status === 'pending_human') {
                                loadDiagnosisReport(targetRecord.id);
                            }
                        }
                        return [2 /*return*/];
                }
            });
        }); };
        var submitFeedback = function () { return __awaiter(_this, void 0, void 0, function () {
            var payload, res, resData, tip, error_20, handleDeleteDiagnosis, handleDeleteDiagnosisFromDetail, handleTabChange, stringify, getAllEvidenceChain, getRootCauseAnalysis, getWhySteps, getTimeline, getImpactScope, getStructuredSolutions, renderHighlight, getEvidenceIcon, getEvidenceTitle, isErrorLog, formatConfigValue, getEventIcon, getEventIconClass, getEventAlertType, getEventAlertClass, formatMetricValue, getMetricValueClass, copyRaw, healthStatusTagType, eventTagType, logLevelTagType, diagnosisStatusTag, formatDiagnoseStatus, sourceText, eventStatusType, formatStatusText, fixConfigDescriptionsWidth;
            var _this = this;
            var _a, _b, _c;
            return __generator(this, function (_d) {
                switch (_d.label) {
                    case 0:
                        if (!diagnosisDrawer.record)
                            return [2 /*return*/];
                        if (!feedbackForm.feedback_type) {
                            element_plus_1.ElMessage.warning('请选择反馈类型');
                            return [2 /*return*/];
                        }
                        if (requiresFeedbackNotes.value && !((_a = feedbackForm.feedback_notes) === null || _a === void 0 ? void 0 : _a.trim())) {
                            element_plus_1.ElMessage.warning('请填写反馈说明');
                            return [2 /*return*/];
                        }
                        payload = {
                            feedback_type: feedbackForm.feedback_type,
                            feedback_notes: ((_b = feedbackForm.feedback_notes) === null || _b === void 0 ? void 0 : _b.trim()) || undefined,
                            action_taken: ((_c = feedbackForm.action_taken) === null || _c === void 0 ? void 0 : _c.trim()) || undefined,
                            iteration_no: feedbackForm.iteration_no
                        };
                        _d.label = 1;
                    case 1:
                        _d.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, (0, observability_1.submitDiagnosisFeedback)(diagnosisDrawer.record.id, payload)];
                    case 2:
                        res = _d.sent();
                        resData = res.data;
                        diagnosisDrawer.record = resData;
                        resetFeedbackForm(resData);
                        tip = payload.feedback_type === 'continue_investigation'
                            ? '反馈已提交，已启动新的诊断迭代'
                            : payload.feedback_type === 'confirmed'
                                ? '反馈已提交，已沉淀到知识库'
                                : '反馈已提交';
                        element_plus_1.ElMessage.success(tip);
                        loadDiagnosis();
                        loadIterationTimeline(resData.id);
                        loadMemoryTimeline(resData.id);
                        if (resData.status === 'pending_human') {
                            loadDiagnosisReport(resData.id);
                        }
                        return [3 /*break*/, 4];
                    case 3:
                        error_20 = _d.sent();
                        if (!isAuthError(error_20)) {
                            element_plus_1.ElMessage.error('反馈提交失败');
                        }
                        return [3 /*break*/, 4];
                    case 4:
                        handleDeleteDiagnosis = function (record) { return __awaiter(_this, void 0, void 0, function () {
                            var error_21;
                            var _a;
                            return __generator(this, function (_b) {
                                switch (_b.label) {
                                    case 0:
                                        _b.trys.push([0, 4, , 5]);
                                        return [4 /*yield*/, element_plus_1.ElMessageBox.confirm("\u786E\u8BA4\u5220\u9664\u8BCA\u65AD\u8BB0\u5F55\u3010".concat(record.resource_name, "\u3011\u5417\uFF1F"), '提示', {
                                                confirmButtonText: '删除',
                                                cancelButtonText: '取消',
                                                type: 'warning'
                                            })];
                                    case 1:
                                        _b.sent();
                                        return [4 /*yield*/, (0, observability_1.deleteDiagnosisRecord)(record.id)];
                                    case 2:
                                        _b.sent();
                                        element_plus_1.ElMessage.success('删除成功');
                                        if (diagnosisDrawer.visible && ((_a = diagnosisDrawer.record) === null || _a === void 0 ? void 0 : _a.id) === record.id) {
                                            diagnosisDrawer.visible = false;
                                            diagnosisDrawer.record = null;
                                        }
                                        return [4 /*yield*/, loadDiagnosis()];
                                    case 3:
                                        _b.sent();
                                        return [3 /*break*/, 5];
                                    case 4:
                                        error_21 = _b.sent();
                                        if (error_21 === 'cancel' || error_21 === 'close') {
                                            return [2 /*return*/];
                                        }
                                        if (!isAuthError(error_21)) {
                                            element_plus_1.ElMessage.error('删除失败');
                                        }
                                        return [3 /*break*/, 5];
                                    case 5: return [2 /*return*/];
                                }
                            });
                        }); };
                        handleDeleteDiagnosisFromDetail = function () { return __awaiter(_this, void 0, void 0, function () {
                            return __generator(this, function (_a) {
                                switch (_a.label) {
                                    case 0:
                                        if (!diagnosisDrawer.record)
                                            return [2 /*return*/];
                                        return [4 /*yield*/, handleDeleteDiagnosis(diagnosisDrawer.record)];
                                    case 1:
                                        _a.sent();
                                        return [2 /*return*/];
                                }
                            });
                        }); };
                        handleTabChange = function (tab) {
                            var _a, _b;
                            if (tab === 'resources') {
                                loadResources();
                            }
                            else if (tab === 'metrics' && metricsResult.value === null) {
                                metricsForm.cluster_id = metricsForm.cluster_id || ((_a = clusters.value[0]) === null || _a === void 0 ? void 0 : _a.id) || 0;
                            }
                            else if (tab === 'logs') {
                                logForm.cluster_id = logForm.cluster_id || ((_b = clusters.value[0]) === null || _b === void 0 ? void 0 : _b.id) || 0;
                            }
                            else if (tab === 'diagnosis') {
                                loadDiagnosis();
                                // 检查是否有进行中的诊断
                                (0, vue_1.nextTick)(function () {
                                    var hasRunningDiagnosis = diagnosisList.value.some(function (record) { var _a; return ['pending', 'running', 'pending_next'].includes(((_a = record.status) === null || _a === void 0 ? void 0 : _a.toLowerCase()) || ''); });
                                    if (hasRunningDiagnosis) {
                                        startDiagnosisPolling();
                                    }
                                });
                            }
                            else {
                                // 切换到其他标签时，停止轮询
                                stopDiagnosisPolling();
                            }
                        };
                        stringify = function (value) {
                            if (!value)
                                return '-';
                            try {
                                return JSON.stringify(value, null, 2);
                            }
                            catch (_a) {
                                return String(value);
                            }
                        };
                        getAllEvidenceChain = function (record) {
                            if (!record)
                                return {};
                            var rootCauseData = getRootCauseAnalysis(record);
                            var evidenceChain = (rootCauseData === null || rootCauseData === void 0 ? void 0 : rootCauseData.evidence_chain) || {};
                            var result = __assign({}, evidenceChain);
                            // 如果 evidence_chain 中没有 logs，尝试从 record.logs 获取
                            if (!result.logs || (Array.isArray(result.logs) && result.logs.length === 0)) {
                                try {
                                    var logsData = record.logs;
                                    if (typeof logsData === 'string') {
                                        try {
                                            logsData = JSON.parse(logsData);
                                        }
                                        catch (_a) {
                                            result.logs = [logsData];
                                            logsData = null;
                                        }
                                    }
                                    if (logsData) {
                                        if (Array.isArray(logsData)) {
                                            result.logs = logsData.filter(function (item) { return item != null; });
                                        }
                                        else if (typeof logsData === 'object') {
                                            var logsObj = logsData;
                                            // 优先从 logs 字段获取（后端返回的格式）
                                            if (logsObj.logs && Array.isArray(logsObj.logs)) {
                                                result.logs = logsObj.logs.filter(function (item) { return item != null; });
                                            }
                                            else if (logsObj.entries && Array.isArray(logsObj.entries)) {
                                                result.logs = logsObj.entries.filter(function (item) { return item != null; });
                                            }
                                            else if (logsObj.results && Array.isArray(logsObj.results)) {
                                                result.logs = logsObj.results.filter(function (item) { return item != null; });
                                            }
                                        }
                                    }
                                }
                                catch (error) {
                                    // 提取日志信息失败，忽略错误
                                }
                            }
                            // 如果 evidence_chain 中没有 metrics，尝试从 record.metrics 获取
                            if (!result.metrics && record.metrics) {
                                try {
                                    var metricsData_1 = record.metrics;
                                    if (typeof metricsData_1 === 'string') {
                                        try {
                                            metricsData_1 = JSON.parse(metricsData_1);
                                        }
                                        catch (_b) {
                                            metricsData_1 = null;
                                        }
                                    }
                                    if (metricsData_1 && typeof metricsData_1 === 'object' && !Array.isArray(metricsData_1)) {
                                        var filteredMetrics_1 = {};
                                        Object.keys(metricsData_1).forEach(function (key) {
                                            var value = metricsData_1[key];
                                            if (value != null && value !== '' && value !== undefined) {
                                                filteredMetrics_1[key] = value;
                                            }
                                        });
                                        if (Object.keys(filteredMetrics_1).length > 0) {
                                            result.metrics = filteredMetrics_1;
                                        }
                                    }
                                }
                                catch (error) {
                                    // 忽略错误
                                }
                            }
                            // 如果 evidence_chain 中没有 events，尝试从 record.events 获取
                            if (!result.events && record.events) {
                                try {
                                    var eventsData = record.events;
                                    if (typeof eventsData === 'string') {
                                        try {
                                            eventsData = JSON.parse(eventsData);
                                        }
                                        catch (_c) {
                                            eventsData = null;
                                        }
                                    }
                                    if (eventsData) {
                                        if (Array.isArray(eventsData) && eventsData.length > 0) {
                                            result.events = eventsData.map(function (event) {
                                                if (typeof event === 'string') {
                                                    return { message: event };
                                                }
                                                return event;
                                            }).filter(function (item) { return item != null; });
                                        }
                                        else if (typeof eventsData === 'object' && !Array.isArray(eventsData)) {
                                            var eventsObj = eventsData;
                                            if (eventsObj.events && Array.isArray(eventsObj.events)) {
                                                result.events = eventsObj.events;
                                            }
                                            else if (eventsObj.list && Array.isArray(eventsObj.list)) {
                                                result.events = eventsObj.list;
                                            }
                                        }
                                    }
                                }
                                catch (error) {
                                    // 忽略错误
                                }
                            }
                            // 如果 evidence_chain 中没有 config 或 config 为空对象，尝试从 symptoms 或 record 中获取
                            var hasConfig = result.config && typeof result.config === 'object' && !Array.isArray(result.config) && Object.keys(result.config).length > 0;
                            if (!hasConfig) {
                                try {
                                    var symptoms = record.symptoms;
                                    if (symptoms) {
                                        // 如果 symptoms 是字符串，尝试解析
                                        var symptomsObj = symptoms;
                                        if (typeof symptoms === 'string') {
                                            try {
                                                symptomsObj = JSON.parse(symptoms);
                                            }
                                            catch (_d) {
                                                symptomsObj = null;
                                            }
                                        }
                                        if (symptomsObj) {
                                            // 优先从 symptoms.config 获取
                                            if (symptomsObj.config) {
                                                var configData = symptomsObj.config;
                                                // 如果 config 是字符串，尝试解析
                                                if (typeof configData === 'string') {
                                                    try {
                                                        configData = JSON.parse(configData);
                                                    }
                                                    catch (_e) {
                                                        // 解析失败，忽略
                                                    }
                                                }
                                                if (configData && typeof configData === 'object' && !Array.isArray(configData) && Object.keys(configData).length > 0) {
                                                    result.config = configData;
                                                }
                                            }
                                            else if (symptomsObj.configuration && typeof symptomsObj.configuration === 'object' && !Array.isArray(symptomsObj.configuration) && Object.keys(symptomsObj.configuration).length > 0) {
                                                result.config = symptomsObj.configuration;
                                            }
                                        }
                                    }
                                    // 如果 symptoms 中没有，尝试从 record 的 config 字段获取
                                    if ((!result.config || (typeof result.config === 'object' && !Array.isArray(result.config) && Object.keys(result.config).length === 0)) && record.config) {
                                        var configData = record.config;
                                        if (typeof configData === 'string') {
                                            try {
                                                configData = JSON.parse(configData);
                                            }
                                            catch (_f) {
                                                configData = null;
                                            }
                                        }
                                        if (configData && typeof configData === 'object' && !Array.isArray(configData) && Object.keys(configData).length > 0) {
                                            result.config = configData;
                                        }
                                    }
                                }
                                catch (error) {
                                    // 提取配置信息失败，忽略错误
                                }
                            }
                            // 过滤掉空值（但保留 config，即使它可能被误判为空）
                            Object.keys(result).forEach(function (key) {
                                var value = result[key];
                                // 对于 config，需要特殊处理：如果它是从 symptoms.config 提取的，即使看起来是空对象也要保留
                                if (key === 'config' && value && typeof value === 'object' && !Array.isArray(value)) {
                                    // 检查 symptoms.config 是否存在且有数据
                                    var symptoms = record.symptoms;
                                    if ((symptoms === null || symptoms === void 0 ? void 0 : symptoms.config) && typeof symptoms.config === 'object' && Object.keys(symptoms.config).length > 0) {
                                        // 如果 symptoms.config 有数据，确保 result.config 使用它
                                        result.config = symptoms.config;
                                        return; // 不删除 config
                                    }
                                }
                                if (!value ||
                                    (Array.isArray(value) && value.length === 0) ||
                                    (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) ||
                                    value === null || value === undefined) {
                                    delete result[key];
                                }
                            });
                            // 最后再次确保 config 存在（如果 symptoms.config 有数据）
                            // 重新获取 symptoms（可能在前面被修改过）
                            var finalSymptoms = record.symptoms;
                            if (typeof finalSymptoms === 'string') {
                                try {
                                    finalSymptoms = JSON.parse(finalSymptoms);
                                }
                                catch (_g) {
                                    finalSymptoms = null;
                                }
                            }
                            if (finalSymptoms === null || finalSymptoms === void 0 ? void 0 : finalSymptoms.config) {
                                var finalConfig = finalSymptoms.config;
                                if (typeof finalConfig === 'string') {
                                    try {
                                        finalConfig = JSON.parse(finalConfig);
                                    }
                                    catch (_h) {
                                        finalConfig = null;
                                    }
                                }
                                if (finalConfig && typeof finalConfig === 'object' && !Array.isArray(finalConfig) && Object.keys(finalConfig).length > 0) {
                                    // 无论 result.config 是否存在或为空，都使用 symptoms.config（因为后端已经提取并存储在这里）
                                    result.config = finalConfig;
                                }
                            }
                            // 最后强制确保 config 存在（无论之前的逻辑如何，只要 symptoms.config 有数据就添加）
                            var forceCheckSymptoms = record.symptoms;
                            var parsedSymptoms = forceCheckSymptoms;
                            // 如果 symptoms 是字符串，先解析
                            if (typeof forceCheckSymptoms === 'string') {
                                try {
                                    parsedSymptoms = JSON.parse(forceCheckSymptoms);
                                }
                                catch (_j) {
                                    parsedSymptoms = null;
                                }
                            }
                            if (parsedSymptoms === null || parsedSymptoms === void 0 ? void 0 : parsedSymptoms.config) {
                                var forceConfig = parsedSymptoms.config;
                                // 如果 config 是字符串，尝试解析
                                if (typeof forceConfig === 'string') {
                                    try {
                                        forceConfig = JSON.parse(forceConfig);
                                    }
                                    catch (_k) {
                                        forceConfig = null;
                                    }
                                }
                                // 无论 result.config 是否存在或为空，都使用 symptoms.config
                                if (forceConfig && typeof forceConfig === 'object' && !Array.isArray(forceConfig) && Object.keys(forceConfig).length > 0) {
                                    result.config = forceConfig;
                                }
                            }
                            return result;
                        };
                        getRootCauseAnalysis = function (record) {
                            var _a, _b;
                            if (!record)
                                return null;
                            var symptoms = record.symptoms;
                            var llmResult = record.recommendations;
                            var report = (_a = diagnosisReport.value) === null || _a === void 0 ? void 0 : _a.report;
                            // 尝试从多个数据源提取证据链
                            var evidenceChain = {};
                            var rootCause = null;
                            var rootCauseAnalysis = null;
                            // 1. 优先从诊断报告中获取
                            if (report) {
                                rootCause = rootCause || report.root_cause;
                                rootCauseAnalysis = rootCauseAnalysis || report.root_cause_analysis;
                                if (report.evidence_chain && typeof report.evidence_chain === 'object') {
                                    evidenceChain = __assign(__assign({}, evidenceChain), report.evidence_chain);
                                }
                            }
                            // 2. 从 llm_result 获取
                            if ((_b = llmResult === null || llmResult === void 0 ? void 0 : llmResult.latest) === null || _b === void 0 ? void 0 : _b.llm_result) {
                                var llmData = llmResult.latest.llm_result;
                                rootCause = rootCause || llmData.root_cause;
                                rootCauseAnalysis = rootCauseAnalysis || llmData.root_cause_analysis;
                                if (llmData.evidence_chain && typeof llmData.evidence_chain === 'object') {
                                    evidenceChain = __assign(__assign({}, evidenceChain), llmData.evidence_chain);
                                }
                            }
                            // 3. 从 symptoms 中获取
                            if (symptoms) {
                                rootCause = rootCause || symptoms.root_cause;
                                rootCauseAnalysis = rootCauseAnalysis || symptoms.root_cause_analysis;
                                if (symptoms.evidence_chain && typeof symptoms.evidence_chain === 'object') {
                                    evidenceChain = __assign(__assign({}, evidenceChain), symptoms.evidence_chain);
                                }
                            }
                            // 4. 从诊断记录的直接字段中提取证据链（logs, metrics, events）- 作为补充
                            // 从 record.logs 提取日志
                            if (record.logs && !evidenceChain.logs) {
                                try {
                                    var logsData = record.logs;
                                    // 如果是字符串，尝试解析
                                    if (typeof logsData === 'string') {
                                        try {
                                            logsData = JSON.parse(logsData);
                                        }
                                        catch (_c) {
                                            // 解析失败，当作普通字符串
                                            evidenceChain.logs = [logsData];
                                            logsData = null;
                                        }
                                    }
                                    if (logsData) {
                                        if (Array.isArray(logsData)) {
                                            evidenceChain.logs = logsData.filter(function (item) { return item != null; });
                                        }
                                        else if (typeof logsData === 'object') {
                                            var logsObj = logsData;
                                            if (logsObj.logs && Array.isArray(logsObj.logs)) {
                                                evidenceChain.logs = logsObj.logs.filter(function (item) { return item != null; });
                                            }
                                            else if (logsObj.entries && Array.isArray(logsObj.entries)) {
                                                evidenceChain.logs = logsObj.entries.filter(function (item) { return item != null; });
                                            }
                                            else if (logsObj.content && Array.isArray(logsObj.content)) {
                                                evidenceChain.logs = logsObj.content.filter(function (item) { return item != null; });
                                            }
                                            else if (logsObj.results && Array.isArray(logsObj.results)) {
                                                evidenceChain.logs = logsObj.results.filter(function (item) { return item != null; });
                                            }
                                            else {
                                                // 如果整个对象就是日志数据，尝试提取所有值
                                                var logEntries = Object.values(logsObj).filter(function (v) { return v != null; });
                                                if (logEntries.length > 0) {
                                                    evidenceChain.logs = logEntries.map(function (v) {
                                                        if (typeof v === 'string')
                                                            return v;
                                                        if (typeof v === 'object' && v.message)
                                                            return v.message;
                                                        return stringify(v);
                                                    }).filter(function (v) { return v && v.trim && v.trim().length > 0; });
                                                }
                                            }
                                        }
                                    }
                                }
                                catch (error) {
                                    // 忽略错误，继续处理其他数据
                                }
                            }
                            // 从 record.metrics 提取指标
                            if (record.metrics && !evidenceChain.metrics) {
                                try {
                                    var metricsData = record.metrics;
                                    // 如果是字符串，尝试解析
                                    if (typeof metricsData === 'string') {
                                        try {
                                            metricsData = JSON.parse(metricsData);
                                        }
                                        catch (_d) {
                                            metricsData = null;
                                        }
                                    }
                                    if (metricsData && typeof metricsData === 'object' && !Array.isArray(metricsData)) {
                                        var metricsObj_1 = metricsData;
                                        // 过滤掉空值
                                        var filteredMetrics_2 = {};
                                        Object.keys(metricsObj_1).forEach(function (key) {
                                            var value = metricsObj_1[key];
                                            if (value != null && value !== '' && value !== undefined) {
                                                // 如果是对象或数组，直接赋值；如果是基本类型，也赋值
                                                filteredMetrics_2[key] = value;
                                            }
                                        });
                                        if (Object.keys(filteredMetrics_2).length > 0) {
                                            evidenceChain.metrics = filteredMetrics_2;
                                        }
                                    }
                                }
                                catch (error) {
                                    // 忽略错误，继续处理其他数据
                                }
                            }
                            // 从 record.events 提取事件
                            if (record.events && !evidenceChain.events) {
                                try {
                                    var eventsData = record.events;
                                    // 如果是字符串，尝试解析
                                    if (typeof eventsData === 'string') {
                                        try {
                                            eventsData = JSON.parse(eventsData);
                                        }
                                        catch (_e) {
                                            eventsData = null;
                                        }
                                    }
                                    if (eventsData) {
                                        if (Array.isArray(eventsData) && eventsData.length > 0) {
                                            evidenceChain.events = eventsData.map(function (event) {
                                                if (typeof event === 'string') {
                                                    return { message: event };
                                                }
                                                return event;
                                            }).filter(function (item) { return item != null; });
                                        }
                                        else if (typeof eventsData === 'object' && !Array.isArray(eventsData)) {
                                            var eventsObj = eventsData;
                                            if (eventsObj.events && Array.isArray(eventsObj.events)) {
                                                evidenceChain.events = eventsObj.events;
                                            }
                                            else if (eventsObj.list && Array.isArray(eventsObj.list)) {
                                                evidenceChain.events = eventsObj.list;
                                            }
                                            else {
                                                // 尝试将对象转换为事件数组
                                                var eventValues = Object.values(eventsObj).filter(function (v) { return v != null; });
                                                if (eventValues.length > 0) {
                                                    evidenceChain.events = eventValues.map(function (v) {
                                                        if (typeof v === 'string')
                                                            return { message: v };
                                                        return v;
                                                    });
                                                }
                                            }
                                        }
                                    }
                                }
                                catch (error) {
                                    // 忽略错误，继续处理其他数据
                                }
                            }
                            // 从 symptoms 中提取配置信息（如果 evidence_chain 中没有 config 或 config 为空对象）
                            if (symptoms && (!evidenceChain.config || (typeof evidenceChain.config === 'object' && !Array.isArray(evidenceChain.config) && Object.keys(evidenceChain.config).length === 0))) {
                                try {
                                    if (symptoms.config && typeof symptoms.config === 'object' && Object.keys(symptoms.config).length > 0) {
                                        evidenceChain.config = symptoms.config;
                                    }
                                    else if (symptoms.configuration && typeof symptoms.configuration === 'object' && Object.keys(symptoms.configuration).length > 0) {
                                        evidenceChain.config = symptoms.configuration;
                                    }
                                    else if (record.config && typeof record.config === 'object' && Object.keys(record.config).length > 0) {
                                        evidenceChain.config = record.config;
                                    }
                                }
                                catch (error) {
                                    // 忽略错误
                                }
                            }
                            // 5. 尝试从迭代历史中提取证据链（从 action_result 中）- 作为最后补充
                            if (iterationTimeline.value.length > 0) {
                                var latestIteration = iterationTimeline.value[0];
                                if (latestIteration === null || latestIteration === void 0 ? void 0 : latestIteration.action_result) {
                                    var actionResult = latestIteration.action_result;
                                    if (Array.isArray(actionResult)) {
                                        var collectDataAction = actionResult.find(function (item) { return item.name === 'collect_data'; });
                                        if (collectDataAction === null || collectDataAction === void 0 ? void 0 : collectDataAction.details) {
                                            var details = collectDataAction.details;
                                            // 补充缺失的证据链数据
                                            if (details.logs && !evidenceChain.logs) {
                                                evidenceChain.logs = Array.isArray(details.logs) ? details.logs : (typeof details.logs === 'number' ? [] : [details.logs]);
                                            }
                                            if (details.metrics && !evidenceChain.metrics) {
                                                evidenceChain.metrics = details.metrics;
                                            }
                                            if (details.config && (!evidenceChain.config || (typeof evidenceChain.config === 'object' && !Array.isArray(evidenceChain.config) && Object.keys(evidenceChain.config).length === 0))) {
                                                evidenceChain.config = details.config;
                                            }
                                            if (details.events && !evidenceChain.events) {
                                                evidenceChain.events = Array.isArray(details.events) ? details.events : [details.events];
                                            }
                                        }
                                    }
                                }
                            }
                            // 过滤掉空值
                            if (evidenceChain && Object.keys(evidenceChain).length > 0) {
                                Object.keys(evidenceChain).forEach(function (key) {
                                    var value = evidenceChain[key];
                                    if (!value ||
                                        (Array.isArray(value) && value.length === 0) ||
                                        (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) ||
                                        value === null || value === undefined) {
                                        delete evidenceChain[key];
                                    }
                                });
                                if (Object.keys(evidenceChain).length === 0) {
                                    evidenceChain = null;
                                }
                            }
                            else {
                                evidenceChain = null;
                            }
                            // 如果有任何数据，返回结果
                            if (rootCause || rootCauseAnalysis || evidenceChain) {
                                return {
                                    root_cause: rootCause,
                                    root_cause_analysis: rootCauseAnalysis,
                                    evidence_chain: evidenceChain
                                };
                            }
                            return null;
                        };
                        getWhySteps = function (rootCauseAnalysis) {
                            if (!rootCauseAnalysis)
                                return [];
                            var steps = [];
                            for (var i = 1; i <= 5; i++) {
                                var why = rootCauseAnalysis["why".concat(i)];
                                if (why) {
                                    steps.push(why);
                                }
                            }
                            return steps;
                        };
                        getTimeline = function (record) {
                            var _a, _b;
                            if (!record)
                                return null;
                            var timeline = null;
                            // 1. 优先从 symptoms 中获取
                            var symptoms = record.symptoms;
                            if (symptoms === null || symptoms === void 0 ? void 0 : symptoms.timeline) {
                                timeline = symptoms.timeline;
                            }
                            // 2. 如果没有，从 llm_result 中获取
                            if (!timeline) {
                                var llmResult = record.recommendations;
                                if ((_b = (_a = llmResult === null || llmResult === void 0 ? void 0 : llmResult.latest) === null || _a === void 0 ? void 0 : _a.llm_result) === null || _b === void 0 ? void 0 : _b.timeline) {
                                    timeline = llmResult.latest.llm_result.timeline;
                                }
                            }
                            // 获取记录的实际时间字段作为回退
                            var recordStartTime = record.started_at || record.created_at;
                            var recordEscalateTime = record.completed_at || record.updated_at || record.started_at || record.created_at;
                            // 检查时间是否合理的辅助函数（检查年份是否合理，2025年及之后）
                            var isValidTime = function (timeStr) {
                                if (!timeStr)
                                    return false;
                                try {
                                    var time = new Date(timeStr);
                                    var year = time.getFullYear();
                                    // 检查年份是否在合理范围内（2024年之后，或者至少是记录创建时间之后）
                                    return year >= 2024;
                                }
                                catch (_a) {
                                    return false;
                                }
                            };
                            // 3. 如果没有时间线数据，使用 record 的时间字段创建默认时间线
                            if (!timeline) {
                                timeline = {
                                    problem_start: recordStartTime,
                                    problem_escalate: recordEscalateTime,
                                    key_events: []
                                };
                            }
                            else {
                                // 4. 如果时间线数据存在但时间字段为空或无效（年份太旧），使用 record 的时间字段作为回退
                                if (!timeline.problem_start || !isValidTime(timeline.problem_start)) {
                                    timeline.problem_start = recordStartTime;
                                }
                                if (!timeline.problem_escalate || !isValidTime(timeline.problem_escalate)) {
                                    timeline.problem_escalate = recordEscalateTime;
                                }
                            }
                            return timeline;
                        };
                        getImpactScope = function (record) {
                            var _a, _b;
                            if (!record)
                                return null;
                            var symptoms = record.symptoms;
                            if (symptoms === null || symptoms === void 0 ? void 0 : symptoms.impact_scope) {
                                return symptoms.impact_scope;
                            }
                            var llmResult = record.recommendations;
                            if ((_b = (_a = llmResult === null || llmResult === void 0 ? void 0 : llmResult.latest) === null || _a === void 0 ? void 0 : _a.llm_result) === null || _b === void 0 ? void 0 : _b.impact_scope) {
                                return llmResult.latest.llm_result.impact_scope;
                            }
                            return null;
                        };
                        getStructuredSolutions = function (record) {
                            var _a;
                            if (!record)
                                return null;
                            var recommendations = record.recommendations;
                            if (recommendations === null || recommendations === void 0 ? void 0 : recommendations.solutions) {
                                return recommendations.solutions;
                            }
                            var llmResult = (_a = recommendations === null || recommendations === void 0 ? void 0 : recommendations.latest) === null || _a === void 0 ? void 0 : _a.llm_result;
                            if (llmResult === null || llmResult === void 0 ? void 0 : llmResult.solutions) {
                                return llmResult.solutions;
                            }
                            return null;
                        };
                        renderHighlight = function (highlight) {
                            if (Array.isArray(highlight)) {
                                return highlight.join('<br>');
                            }
                            return highlight;
                        };
                        getEvidenceIcon = function (key) {
                            var keyLower = key.toLowerCase();
                            if (keyLower === 'logs')
                                return 'Document';
                            if (keyLower === 'config')
                                return 'Setting';
                            if (keyLower === 'events')
                                return 'Bell';
                            if (keyLower === 'metrics')
                                return 'DataAnalysis';
                            return 'InfoFilled';
                        };
                        getEvidenceTitle = function (key) {
                            var keyLower = key.toLowerCase();
                            var titleMap = {
                                logs: '日志信息',
                                config: '配置信息',
                                events: '事件信息',
                                metrics: '指标信息'
                            };
                            return titleMap[keyLower] || key;
                        };
                        isErrorLog = function (item) {
                            if (typeof item === 'string') {
                                var lower = item.toLowerCase();
                                return lower.includes('error') ||
                                    lower.includes('failed') ||
                                    lower.includes('exception') ||
                                    lower.includes('oom') ||
                                    lower.includes('killed');
                            }
                            if (item && typeof item === 'object') {
                                var str = stringify(item).toLowerCase();
                                return str.includes('error') ||
                                    str.includes('failed') ||
                                    str.includes('exception') ||
                                    str.includes('oom') ||
                                    str.includes('killed');
                            }
                            return false;
                        };
                        formatConfigValue = function (value) {
                            if (value === null || value === undefined)
                                return '-';
                            if (typeof value === 'object') {
                                return stringify(value);
                            }
                            return String(value);
                        };
                        getEventIcon = function (item) {
                            if (typeof item === 'string') {
                                var lower = item.toLowerCase();
                                if (lower.includes('error') || lower.includes('failed') || lower.includes('killed')) {
                                    return 'CircleCloseFilled';
                                }
                                if (lower.includes('success') || lower.includes('started') || lower.includes('completed')) {
                                    return 'CircleCheckFilled';
                                }
                            }
                            if (item && typeof item === 'object') {
                                var str = stringify(item).toLowerCase();
                                if (str.includes('error') || str.includes('failed') || str.includes('killed')) {
                                    return 'CircleCloseFilled';
                                }
                                if (str.includes('success') || str.includes('started') || str.includes('completed')) {
                                    return 'CircleCheckFilled';
                                }
                            }
                            return 'InfoFilled';
                        };
                        getEventIconClass = function (item) {
                            var icon = getEventIcon(item);
                            if (icon === 'CircleCloseFilled')
                                return 'event-icon-error';
                            if (icon === 'CircleCheckFilled')
                                return 'event-icon-success';
                            return 'event-icon-info';
                        };
                        getEventAlertType = function (item) {
                            if (typeof item === 'string') {
                                var lower = item.toLowerCase();
                                if (lower.includes('error') || lower.includes('failed') || lower.includes('killed') || lower.includes('oom')) {
                                    return 'error';
                                }
                                if (lower.includes('success') || lower.includes('started') || lower.includes('completed')) {
                                    return 'success';
                                }
                                if (lower.includes('warning') || lower.includes('warn')) {
                                    return 'warning';
                                }
                            }
                            if (item && typeof item === 'object') {
                                var str = stringify(item).toLowerCase();
                                if (str.includes('error') || str.includes('failed') || str.includes('killed') || str.includes('oom')) {
                                    return 'error';
                                }
                                if (str.includes('success') || str.includes('started') || str.includes('completed')) {
                                    return 'success';
                                }
                                if (str.includes('warning') || str.includes('warn')) {
                                    return 'warning';
                                }
                            }
                            return 'info';
                        };
                        getEventAlertClass = function (item) {
                            var type = getEventAlertType(item);
                            return "event-alert-".concat(type);
                        };
                        formatMetricValue = function (value) {
                            if (value === null || value === undefined)
                                return '-';
                            if (typeof value === 'number') {
                                // 如果是百分比，显示百分比
                                if (value > 0 && value <= 1) {
                                    return "".concat((value * 100).toFixed(2), "%");
                                }
                                // 如果是大数字，格式化
                                if (value >= 1000) {
                                    return value.toLocaleString();
                                }
                                return value.toString();
                            }
                            return String(value);
                        };
                        getMetricValueClass = function (value) {
                            if (typeof value === 'number') {
                                // 如果是百分比
                                if (value > 0 && value <= 1) {
                                    if (value > 0.8)
                                        return 'metric-value-danger';
                                    if (value > 0.6)
                                        return 'metric-value-warning';
                                    return 'metric-value-success';
                                }
                                // 如果是内存值（Mi）
                                if (String(value).includes('Mi') || String(value).includes('Gi')) {
                                    return 'metric-value-info';
                                }
                            }
                            return 'metric-value-info';
                        };
                        (0, vue_1.watch)(function () { return diagnosisDrawer.visible; }, function (visible) {
                            if (!visible) {
                                iterationTimeline.value = [];
                                memoryTimeline.value = [];
                                diagnosisReport.value = null;
                            }
                        });
                        copyRaw = function (payload) { return __awaiter(_this, void 0, void 0, function () {
                            var _a;
                            return __generator(this, function (_b) {
                                switch (_b.label) {
                                    case 0:
                                        _b.trys.push([0, 2, , 3]);
                                        return [4 /*yield*/, navigator.clipboard.writeText(stringify(payload))];
                                    case 1:
                                        _b.sent();
                                        element_plus_1.ElMessage.success('已复制到剪贴板');
                                        return [3 /*break*/, 3];
                                    case 2:
                                        _a = _b.sent();
                                        element_plus_1.ElMessage.error('复制失败');
                                        return [3 /*break*/, 3];
                                    case 3: return [2 /*return*/];
                                }
                            });
                        }); };
                        healthStatusTagType = function (status) {
                            switch ((status || '').toLowerCase()) {
                                case 'ok':
                                case 'healthy':
                                    return 'success';
                                case 'warning':
                                    return 'warning';
                                case 'error':
                                case 'unhealthy':
                                    return 'danger';
                                default:
                                    return 'info';
                            }
                        };
                        eventTagType = function (type) {
                            switch (type) {
                                case 'created':
                                    return 'success';
                                case 'updated':
                                    return 'warning';
                                case 'deleted':
                                    return 'danger';
                                default:
                                    return 'info';
                            }
                        };
                        logLevelTagType = function (level) {
                            var normalized = (level || '').toLowerCase();
                            if (['error', 'err', 'critical', 'fatal'].includes(normalized))
                                return 'danger';
                            if (['warn', 'warning'].includes(normalized))
                                return 'warning';
                            if (['info', 'notice'].includes(normalized))
                                return 'info';
                            if (['debug', 'trace'].includes(normalized))
                                return 'success';
                            return 'default';
                        };
                        diagnosisStatusTag = function (status) {
                            switch ((status || '').toLowerCase()) {
                                case 'completed':
                                    return 'success';
                                case 'running':
                                    return 'warning';
                                case 'pending_next':
                                    return 'warning';
                                case 'pending_human':
                                    return 'info';
                                case 'failed':
                                    return 'danger';
                                default:
                                    return 'info';
                            }
                        };
                        formatDiagnoseStatus = function (status) {
                            switch ((status || '').toLowerCase()) {
                                case 'completed':
                                    return '已完成';
                                case 'running':
                                    return '诊断中';
                                case 'pending_next':
                                    return '等待下一轮';
                                case 'pending_human':
                                    return '待人工处理';
                                case 'failed':
                                    return '失败';
                                default:
                                    return status || '未知';
                            }
                        };
                        sourceText = function (source) {
                            switch ((source || '').toLowerCase()) {
                                case 'kb':
                                    return '知识库';
                                case 'llm':
                                    return '大模型';
                                case 'rules':
                                    return '规则引擎';
                                case 'search':
                                    return '外部搜索';
                                default:
                                    return source || '-';
                            }
                        };
                        eventStatusType = function (status) {
                            switch ((status || '').toLowerCase()) {
                                case 'error':
                                case 'exception':
                                    return 'danger';
                                case 'success':
                                case 'ok':
                                    return 'success';
                                case 'warning':
                                    return 'warning';
                                default:
                                    return 'info';
                            }
                        };
                        formatStatusText = function (status) {
                            if (!status)
                                return '未知';
                            switch (status.toLowerCase()) {
                                case 'ok':
                                    return '正常';
                                case 'healthy':
                                    return '健康';
                                case 'warning':
                                    return '警告';
                                case 'error':
                                case 'unhealthy':
                                    return '异常';
                                default:
                                    return status;
                            }
                        };
                        (0, vue_1.watch)(function () { return resourceFilters.clusterId; }, function () {
                            resourceFilters.page = 1;
                            loadResources();
                        });
                        (0, vue_1.watch)(function () { return metricsForm.cluster_id; }, function () {
                            metricsResult.value = null;
                        });
                        (0, vue_1.watch)(function () { return logForm.cluster_id; }, function () {
                            logResult.value = null;
                        });
                        (0, vue_1.onMounted)(function () { return __awaiter(_this, void 0, void 0, function () {
                            var hasRunningDiagnosis;
                            return __generator(this, function (_a) {
                                switch (_a.label) {
                                    case 0: return [4 /*yield*/, loadClusters()];
                                    case 1:
                                        _a.sent();
                                        if (activeTab.value === 'resources') {
                                            loadResources();
                                        }
                                        if (!(activeTab.value === 'diagnosis')) return [3 /*break*/, 4];
                                        return [4 /*yield*/, loadDiagnosis()
                                            // 检查是否有进行中的诊断，如果有则启动轮询
                                        ];
                                    case 2:
                                        _a.sent();
                                        // 检查是否有进行中的诊断，如果有则启动轮询
                                        return [4 /*yield*/, (0, vue_1.nextTick)()];
                                    case 3:
                                        // 检查是否有进行中的诊断，如果有则启动轮询
                                        _a.sent();
                                        hasRunningDiagnosis = diagnosisList.value.some(function (record) { var _a; return ['pending', 'running', 'pending_next'].includes(((_a = record.status) === null || _a === void 0 ? void 0 : _a.toLowerCase()) || ''); });
                                        if (hasRunningDiagnosis) {
                                            startDiagnosisPolling();
                                        }
                                        _a.label = 4;
                                    case 4:
                                        // 设置配置信息表格列宽
                                        fixConfigDescriptionsWidth();
                                        return [2 /*return*/];
                                }
                            });
                        }); });
                        (0, vue_1.onUnmounted)(function () {
                            // 清理定时器
                            stopDiagnosisPolling();
                        });
                        fixConfigDescriptionsWidth = function () {
                            (0, vue_1.nextTick)(function () {
                                var configDescriptions = document.querySelectorAll('.config-descriptions .el-descriptions__table');
                                configDescriptions.forEach(function (table) {
                                    // 设置 table-layout
                                    if (table) {
                                        table.style.tableLayout = 'fixed';
                                        table.style.width = '100%';
                                        // 设置 colgroup
                                        var colgroup = table.querySelector('colgroup');
                                        if (!colgroup) {
                                            colgroup = document.createElement('colgroup');
                                            table.insertBefore(colgroup, table.firstChild);
                                        }
                                        // 确保有两个 col 元素
                                        var cols = colgroup.querySelectorAll('col');
                                        if (cols.length < 2) {
                                            colgroup.innerHTML = '<col style="width: 50% !important;"><col style="width: 50% !important;">';
                                        }
                                        else {
                                            cols.forEach(function (col) {
                                                col.style.width = '50%';
                                                col.style.minWidth = '50%';
                                                col.style.maxWidth = '50%';
                                            });
                                        }
                                        // 强制设置 td 宽度，并防止文本溢出
                                        var tds = table.querySelectorAll('tbody td');
                                        tds.forEach(function (td, index) {
                                            if (index % 2 === 0) {
                                                // 第一列（标签列）
                                                td.style.width = '50%';
                                                td.style.minWidth = '50%';
                                                td.style.maxWidth = '50%';
                                                td.style.boxSizing = 'border-box';
                                                td.style.overflow = 'hidden';
                                                td.style.wordBreak = 'break-word';
                                                td.style.overflowWrap = 'break-word';
                                                // 确保标签列内容不会溢出
                                                var label = td.querySelector('.el-descriptions__label');
                                                if (label) {
                                                    label.style.width = '100%';
                                                    label.style.maxWidth = '100%';
                                                    label.style.boxSizing = 'border-box';
                                                    label.style.overflow = 'hidden';
                                                    label.style.wordBreak = 'break-word';
                                                    label.style.overflowWrap = 'break-word';
                                                    label.style.whiteSpace = 'normal';
                                                }
                                            }
                                            else {
                                                // 第二列（内容列）
                                                td.style.width = '50%';
                                                td.style.minWidth = '50%';
                                                td.style.maxWidth = '50%';
                                                td.style.boxSizing = 'border-box';
                                                td.style.overflow = 'hidden';
                                                td.style.wordBreak = 'break-word';
                                                td.style.overflowWrap = 'break-word';
                                                // 确保内容列内容不会溢出
                                                var content = td.querySelector('.el-descriptions__content');
                                                if (content) {
                                                    content.style.width = '100%';
                                                    content.style.maxWidth = '100%';
                                                    content.style.boxSizing = 'border-box';
                                                    content.style.overflow = 'hidden';
                                                    content.style.wordBreak = 'break-word';
                                                    content.style.overflowWrap = 'break-word';
                                                    content.style.whiteSpace = 'normal';
                                                }
                                            }
                                        });
                                    }
                                });
                            });
                        };
                        // 在组件更新后设置列宽
                        (0, vue_1.onUpdated)(function () {
                            fixConfigDescriptionsWidth();
                        });
                        return [2 /*return*/, {
                                Monitor: icons_vue_1.Monitor,
                                ArrowDown: icons_vue_1.ArrowDown,
                                MoreFilled: icons_vue_1.MoreFilled,
                                Edit: icons_vue_1.Edit,
                                Delete: icons_vue_1.Delete,
                                activeTab: activeTab,
                                pageLoading: pageLoading,
                                clusters: clusters,
                                clusterPagination: clusterPagination,
                                clusterDialog: clusterDialog,
                                clusterFormRef: clusterFormRef,
                                clusterRules: clusterRules,
                                openClusterDialog: openClusterDialog,
                                submitClusterForm: submitClusterForm,
                                handleDeleteCluster: handleDeleteCluster,
                                handleTestConnectivity: handleTestConnectivity,
                                handleHealthCheck: handleHealthCheck,
                                loadClusters: loadClusters,
                                PROM_AUTH_OPTIONS: PROM_AUTH_OPTIONS,
                                LOG_AUTH_OPTIONS: LOG_AUTH_OPTIONS,
                                connectivityDialog: connectivityDialog,
                                healthStatusTagType: healthStatusTagType,
                                formatStatusText: formatStatusText,
                                resourceTypeOptions: resourceTypeOptions,
                                resourceFilters: resourceFilters,
                                resourceSnapshots: resourceSnapshots,
                                resourceLoading: resourceLoading,
                                resourcePagination: resourcePagination,
                                loadResources: loadResources,
                                handleResourcePageChange: handleResourcePageChange,
                                handleManualSync: handleManualSync,
                                recentSyncEvents: recentSyncEvents,
                                eventTagType: eventTagType,
                                stringify: stringify,
                                metricTemplateOptions: metricTemplateOptions,
                                defaultTimeRange: defaultTimeRange,
                                metricsForm: metricsForm,
                                metricsResult: metricsResult,
                                metricsSeries: metricsSeries,
                                chartOptions: chartOptions,
                                handleTemplateChange: handleTemplateChange,
                                handleQueryMetrics: handleQueryMetrics,
                                resetMetricsForm: resetMetricsForm,
                                needsNamespace: needsNamespace,
                                needsPod: needsPod,
                                needsWindow: needsWindow,
                                namespaceLoading: namespaceLoading,
                                podLoading: podLoading,
                                namespaces: namespaces,
                                pods: pods,
                                handleNamespaceChange: handleNamespaceChange,
                                logForm: logForm,
                                logResult: logResult,
                                handleQueryLogs: handleQueryLogs,
                                resetLogForm: resetLogForm,
                                renderHighlight: renderHighlight,
                                logLevelTagType: logLevelTagType,
                                diagnosisPagination: diagnosisPagination,
                                diagnosisList: diagnosisList,
                                diagnosisLoading: diagnosisLoading,
                                loadDiagnosis: loadDiagnosis,
                                diagnosisStatusTag: diagnosisStatusTag,
                                formatDiagnoseStatus: formatDiagnoseStatus,
                                sourceText: sourceText,
                                diagnosisDialog: diagnosisDialog,
                                diagnosisNamespaces: diagnosisNamespaces,
                                diagnosisNamespaceLoading: diagnosisNamespaceLoading,
                                diagnosisResources: diagnosisResources,
                                diagnosisResourceLoading: diagnosisResourceLoading,
                                openManualDiagnosis: openManualDiagnosis,
                                handleDiagnosisClusterChange: handleDiagnosisClusterChange,
                                handleDiagnosisNamespaceChange: handleDiagnosisNamespaceChange,
                                handleDiagnosisResourceTypeChange: handleDiagnosisResourceTypeChange,
                                submitManualDiagnosis: submitManualDiagnosis,
                                diagnosisDrawer: diagnosisDrawer,
                                diagnosisUpdatedAt: diagnosisUpdatedAt,
                                diagnosisConfidencePercent: diagnosisConfidencePercent,
                                diagnosisConfidenceStatus: diagnosisConfidenceStatus,
                                feedbackForm: feedbackForm,
                                feedbackOptions: feedbackOptions,
                                requiresFeedbackNotes: requiresFeedbackNotes,
                                feedbackNotesPlaceholder: feedbackNotesPlaceholder,
                                iterationOptions: iterationOptions,
                                feedbackState: feedbackState,
                                feedbackStateDescription: feedbackStateDescription,
                                feedbackLatest: feedbackLatest,
                                formatFeedbackType: formatFeedbackType,
                                submitFeedback: submitFeedback,
                                iterationLoading: iterationLoading,
                                iterationTimeline: iterationTimeline,
                                memoryLoading: memoryLoading,
                                memoryTimeline: memoryTimeline,
                                diagnosisReport: diagnosisReport,
                                openDiagnosisDetail: openDiagnosisDetail,
                                handleDeleteDiagnosis: handleDeleteDiagnosis,
                                handleDeleteDiagnosisFromDetail: handleDeleteDiagnosisFromDetail,
                                getRootCauseAnalysis: getRootCauseAnalysis,
                                getWhySteps: getWhySteps,
                                getTimeline: getTimeline,
                                getImpactScope: getImpactScope,
                                getStructuredSolutions: getStructuredSolutions,
                                eventStatusType: eventStatusType,
                                copyRaw: copyRaw,
                                handleTabChange: handleTabChange,
                                formatDateTime: format_1.formatDateTime,
                                getEvidenceIcon: getEvidenceIcon,
                                getEvidenceTitle: getEvidenceTitle,
                                isErrorLog: isErrorLog,
                                formatConfigValue: formatConfigValue,
                                getEventIcon: getEventIcon,
                                getEventIconClass: getEventIconClass,
                                getEventAlertType: getEventAlertType,
                                getEventAlertClass: getEventAlertClass,
                                formatMetricValue: formatMetricValue,
                                getMetricValueClass: getMetricValueClass,
                                getAllEvidenceChain: getAllEvidenceChain
                            }];
                }
            });
        }); };
    }
});
