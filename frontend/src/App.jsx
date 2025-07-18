import React, { useState, useMemo, useCallback } from 'react';
import {
  Form, Input, Button, Table, notification, Spin, Card, Row, Col, Space, Tag, Tabs
} from 'antd';
import {
  LoadingOutlined, ExclamationCircleOutlined
} from '@ant-design/icons';
import axios from 'axios';

// ========== JIRA 分配/分析 相关 ==========
const decodeUnicode = (str) => {
  try {
    return decodeURIComponent(JSON.parse('"' + str.replace(/"/g, '\\"') + '"'));
  } catch {
    return str;
  }
};
const containerStyle = { margin: 24, borderRadius: 8, boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' };
const formItemStyle = { marginBottom: 16 };

const jiraApi = axios.create({
  baseURL: 'http://127.0.0.1:5001',
  timeout: 3000000,
});
jiraApi.interceptors.request.use(config => {
  config.headers['Content-Type'] = 'application/json';
  return config;
});
jiraApi.interceptors.response.use(
  response => response,
  error => {
    const errorMessage = error.response?.data?.message ||
      error.code === 'ECONNABORTED' ? '请求超时' : '服务异常';
    notification.error({ message: '请求失败', description: errorMessage });
    return Promise.reject(error);
  }
);

const AnalysisDetail = ({ reasoning }) => {
  const decodedText = useMemo(() => {
    try {
      return decodeURIComponent(JSON.parse('"' + reasoning.replace(/"/g, '\\"') + '"'));
    } catch {
      return reasoning;
    }
  }, [reasoning]);

  return (
    <div style={{ maxWidth: 800 }}>
      <div style={{
        padding: 16,
        backgroundColor: '#f8f9fa',
        borderRadius: 8,
      }}>
        <div style={{
          maxHeight: '60vh',
          overflowY: 'auto',
          padding: 12,
          background: 'white',
          borderRadius: 4,
          border: '1px solid #f0f0f0'
        }}>
          <pre style={{
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word',
            margin: 0,
            fontFamily: 'Monaco, Consolas, monospace',
            fontSize: 12
          }}>
            {decodedText || '未获取到分析内容'}
          </pre>
        </div>
      </div>
    </div>
  );
};

function JiraPanel() {
  const [form] = Form.useForm();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingType, setLoadingType] = useState('');
  const [cookieError, setCookieError] = useState('');

  const columns = useMemo(() => [
    {
      title: 'URL',
      dataIndex: 'url',
      key: 'url',
      ellipsis: true,
      width: 140,
      render: (text) => (
        <a href={text} target="_blank" rel="noopener noreferrer"
          style={{ color: '#1890ff', textDecoration: 'underline' }}>
          {text}
        </a>
      )
    },
    { title: '描述', dataIndex: 'description', key: 'description', width: 360 },
    { title: 'ID', dataIndex: 'id', key: 'id', width: 50 },
    {
      title: '负责人', dataIndex: 'assignee', key: 'assignee', width: 50,
      render: (text, record) => (
        <Input
          value={text}
          onChange={(e) => handleAssigneeChange(record.key, e.target.value)}
          placeholder="输入负责人"
        />
      ),
    },
    {
      title: '操作', key: 'action', width: 100,
      render: (_, record) => (
        <Space>
          <Button type="primary" danger onClick={() => handleDelete(record.key)} size="small">删除</Button>
          <Button type="default" onClick={() => handleAddLabel(record.id)} size="small">重点问题分析</Button>
        </Space>
      ),
    },
    {
      title: 'AI分析', key: 'analysis', width: 100,
      render: (_, record) => (
        <Button type="link" onClick={() => {
          notification.open({
            message: <span style={{ fontSize: 16 }}>AI分析详情</span>,
            description: <AnalysisDetail reasoning={record.reasoning} />,
            duration: 0,
            style: { width: 800, marginLeft: -384 }
          });
        }}>查看逻辑</Button>
      ),
    },
  ], []);

  const handleAssigneeChange = useCallback((key, value) => {
    setData(prev => prev.map(item =>
      item.key === key ? { ...item, assignee: value } : item
    ));
  }, []);
  const handleDelete = useCallback((key) => {
    setData(prev => prev.filter(item => item.key !== key));
  }, []);
  const handleAnalyze = async (values) => {
    setLoading(true); setLoadingType('analyze');
    try {
      const response = await jiraApi.post('/analyze', {
        jira_url: values.jiraUrl,
        cookies: values.cookieInput,
      });
      setData(response.data.results.map((item, index) => ({
        key: index,
        ...item,
        assignee: item.assignee || '',
        reasoning: item.reasoning || '无分析记录'
      })));
      notification.success({ message: '数据分析成功' });
    } catch (error) { }
    finally { setLoading(false); setLoadingType(''); }
  };
  const handleConfirm = async () => {
    setLoading(true); setLoadingType('assign');
    try {
      await jiraApi.post('/assign', { data, cookies: form.getFieldValue('cookieInput') });
      notification.success({ message: '分配任务成功' });
    } catch (error) { }
    finally { setLoading(false); setLoadingType(''); }
  };
  const handleAddLabel = async (issueId) => {
    try {
      await jiraApi.post('/add-label', {
        issueId,
        labels: "重点问题分析",
        cookieInput: form.getFieldValue('cookieInput')
      });
      notification.success({ message: '标签添加成功', description: `已为问题 ${issueId} 添加标签` });
    } catch (error) {
      notification.error({
        message: '标签添加失败',
        description: error.response?.data?.error || '请检查网络连接'
      });
    }
  };
  const tableFooter = () => (
    <div style={{ textAlign: 'right', padding: '8px 16px' }}>
      <Tag color="blue">总行数: {data.length}</Tag>
    </div>
  );
  const validateCookie = () => {
    try {
      const cookieInput = form.getFieldValue('cookieInput').trim();
      if (!cookieInput) throw new Error('请输入Cookie信息');
      const requiredCookies = ['JSESSIONID', 'atlassian.xsrf.token'];
      const isValid = requiredCookies.every(cookie =>
        cookieInput.includes(`${cookie}=`)
      );
      if (!isValid) throw new Error('缺少必要Cookie字段');
      setCookieError('');
      return true;
    } catch (error) {
      setCookieError(
        <span style={{ color: '#ff4d4f' }}>
          <ExclamationCircleOutlined /> {error.message}
        </span>
      );
      return false;
    }
  };

  return (
    <Card title="JIRA 数据分析与分配系统" headStyle={{ background: '#f0f2f5' }} style={containerStyle}>
      <Form
        form={form}
        initialValues={{
          jiraUrl: 'https://gfjira.yyrd.com/browse/HXRL-103987?filter=83510',
          cookieInput: ''
        }}
        onFinish={handleAnalyze}
        layout="vertical"
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="JIRA看板URL"
              name="jiraUrl"
              rules={[{ required: true, message: '请输入URL' }]}
              style={formItemStyle}
            >
              <Input placeholder="输入JIRA看板URL" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="Cookie信息"
              name="cookieInput"
              help={cookieError}
              style={formItemStyle}
            >
              <Input.Search
                placeholder="输入Cookie（name=value）"
                enterButton={
                  <Button icon={<ExclamationCircleOutlined />}>
                    验证
                  </Button>
                }
                onSearch={validateCookie}
              />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading} style={{ width: 120 }}>
              开始分析
            </Button>
            <Button type="primary" onClick={handleConfirm} disabled={!data.length || loading} style={{ width: 120 }}>
              确认分配
            </Button>
          </Space>
        </Form.Item>
      </Form>
      <Spin tip={`正在${loadingType === 'analyze' ? '分析数据' : '分配任务'}...`}
        spinning={loading} indicator={<LoadingOutlined spin />}>
        <Table
          columns={columns}
          dataSource={data}
          bordered
          pagination={false}
          scroll={{ y: 500 }}
          rowClassName={(_, index) => index % 2 === 0 ? 'even-row' : 'odd-row'}
          footer={tableFooter}
        />
      </Spin>
      <style>{`
        .ant-table-thead > tr > th { background: #fafafa !important; }
        .even-row { background-color: #f8f9fa; }
        .odd-row { background-color: white; }
        .ant-notification-notice-description {
            max-height: 60vh !important;
            overflow-y: auto !important;
        }
      `}</style>
    </Card>
  );
}

// ========== Git提交点对比 相关 ==========

const GIT_API_BASE = 'http://localhost:5001'; // 你main.py的端口
const DEFAULT_REMOTE = "git@git.yyrd.com:hrcloud/hrcloud-corehr-process.git";
const BRANCHES = ["hotfix/20250711-fix", "release", "daily", "develop","origin/hotfix/20250711-fix", "origin/release", "origin/daily", "origin/develop"];

function GitComparePanel() {
  const [repoUrl, setRepoUrl] = useState(DEFAULT_REMOTE);
  const [sourceBranch, setSourceBranch] = useState("release");
  const [targetBranch, setTargetBranch] = useState("daily");
  const [startCommit, setStartCommit] = useState("");
  const [checkAll, setCheckAll] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleCompare = async () => {
    setLoading(true);
    setResult(null);
    setError("");
    try {
      const res = await axios.post(`${GIT_API_BASE}/api/compare-commits`, {
        repo_url: repoUrl,
        source_branch: sourceBranch,
        target_branch: targetBranch,
        start_commit: startCommit,
        check_all: checkAll,
      });
      setResult(res.data);
    } catch (err) {
      setError(err.message || "请求出错，请检查后端服务");
    }
    setLoading(false);
  };

  return (
    <Card title="Git提交点分支对比工具" headStyle={{ background: '#f0f2f5' }} style={containerStyle}>
      <div style={{ marginBottom: 12 }}>
        <label>仓库地址：</label>
        <Input
          style={{ width: 400 }}
          value={repoUrl}
          onChange={e => setRepoUrl(e.target.value)}
        />
      </div>
      <div style={{ marginBottom: 12 }}>
        <label>源分支：</label>
        <select value={sourceBranch} onChange={e => setSourceBranch(e.target.value)}>
          {BRANCHES.map(b => <option key={b} value={b}>{b}</option>)}
        </select>
        <label style={{ marginLeft: 20 }}>目标分支：</label>
        <select value={targetBranch} onChange={e => setTargetBranch(e.target.value)}>
          {BRANCHES.map(b => <option key={b} value={b}>{b}</option>)}
        </select>
      </div>
      <div style={{ marginBottom: 12 }}>
        <label>起始提交点（commit hash）：</label>
        <Input
          style={{ width: 350 }}
          value={startCommit}
          onChange={e => setStartCommit(e.target.value)}
          placeholder="如 888c06c4, 可从git log复制"
        />
      </div>
      <div style={{ marginBottom: 12 }}>
        <label>
          <input
            type="checkbox"
            checked={checkAll}
            onChange={e => setCheckAll(e.target.checked)}
          />
          检查起始提交点及之后所有提交
        </label>
      </div>
      <Button type="primary" onClick={handleCompare} disabled={loading}>
        {loading ? "对比中..." : "开始对比"}
      </Button>
      {error && <div style={{ color: "red", marginTop: 16 }}>{error}</div>}


      {
        result && (
          <div>
            <div>
              <b>源分支：</b>{result.source_branch}<br/>
              <b>目标分支：</b>{result.target_branch}<br/>
              <b>提交总数：</b>{result.checked_count}<br/>
              <b>目标分支包含提交数：</b>{result.matched_count}<br/>
              <b>目标分支未包含提交数：</b>{result.unmatched_count}<br/>
            </div>
            <hr />
            <div>
              <h3>✅ 已在目标分支的提交：</h3>
              <ul>
                {(result.matched || []).map(item => (
                  <li key={item.commit}>
                    <span>{item.commit.slice(0, 8)}</span> - <span>【{item.author}】</span> - <span>【{item.date}】</span>
                    - <span>{item.message}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 style={{color:'red'}}>❌ 未在目标分支的提交：</h3>
              <ul>
                {(result.unmatched || []).map(item => (
                    <li key={item.commit}>
                      <span>{item.commit.slice(0, 8)}</span> - <span>【{item.author}】</span> - <span>【{item.date}】</span>
                       - <span>{item.message}</span>
                    </li>
                ))}
              </ul>
            </div>
          </div>
        )
      }
    </Card>
  );
}

// ========== 页面Tabs整合 ==========
const {TabPane} = Tabs;

export default function App() {
  const [tab, setTab] = useState("jira");

  return (
      <div style={{minHeight: '100vh', background: '#f7f8fa', padding: '0 0 48px 0'}}>
        <Tabs activeKey={tab} onChange={setTab} centered size="large" style={{margin: '20px 0 24px 0'}}>
          <TabPane tab="JIRA 分析与分配" key="jira"/>
          <TabPane tab="Git提交点分支对比" key="git"/>
        </Tabs>
        {tab === "jira" ? <JiraPanel/> : <GitComparePanel />}
    </div>
  );
}