import React, { useState, useMemo, useCallback } from 'react';
import {
  Form,
  Input,
  Button,
  Table,
  notification,
  Spin,
  Card,
  Row,
  Col,
  Space, Tag
} from 'antd';
import {
  LoadingOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import axios from 'axios';



// 在App.js顶部添加解码函数
const decodeUnicode = (str) => {
  try {
    return decodeURIComponent(JSON.parse('"' + str.replace(/"/g, '\\"') + '"'));
  } catch {
    return str;
  }
};


// 样式常量
const containerStyle = {
  margin: 24,
  borderRadius: 8,
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
};

const formItemStyle = {
  marginBottom: 16
};

// 创建axios实例
const api = axios.create({
  baseURL: 'http://127.0.0.1:5000',
  timeout: 3000000,
});

// 请求拦截器
api.interceptors.request.use(config => {
  config.headers['Content-Type'] = 'application/json';
  return config;
});

// 响应拦截器
api.interceptors.response.use(
  response => response,
  error => {
    const errorMessage = error.response?.data?.message ||
      error.code === 'ECONNABORTED' ? '请求超时' : '服务异常';

    notification.error({
      message: '请求失败',
      description: errorMessage
    });
    return Promise.reject(error);
  }
);

function App() {
  const [form] = Form.useForm();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingType, setLoadingType] = useState('');
  const [cookieError, setCookieError] = useState('');

  // 优化列配置
  const columns = useMemo(() => [
    {
      title: 'URL',
      dataIndex: 'url',
      key: 'url',
      ellipsis: true,
      width: 140,  // 调整宽度
      render: (text) => (
      <a
        href={text}
        target="_blank"
        rel="noopener noreferrer"
        style={{ color: '#1890ff', textDecoration: 'underline' }}
      >
        {text}
      </a>
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 360  // 调整宽度
    },
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 50  // 调整宽度
    },
    {
      title: '负责人',
      dataIndex: 'assignee',
      key: 'assignee',
      width: 50,  // 调整宽度
      render: (text, record) => (
        <Input
          value={text}
          onChange={(e) => handleAssigneeChange(record.key, e.target.value)}
          placeholder="输入负责人"
        />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,  // 加宽操作列
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            danger
            onClick={() => handleDelete(record.key)}
            size="small"
          >
            删除
          </Button>
          <Button
            type="default"
            onClick={() => handleAddLabel(record.id)}
            size="small"
          >
            重点问题分析
          </Button>
        </Space>
      ),
    },
    {
    title: 'AI分析',
    key: 'analysis',
    width: 100,
    render: (_, record) => (
      <Button
        type="link"
        onClick={() => {
          notification.open({
            message: <span style={{ fontSize: 16 }}>AI分析详情</span>,
            description: <AnalysisDetail reasoning={record.reasoning} />,
            duration: 0,
            style: {
              width: 800,
              marginLeft: -384 // 居中修正
            }
          });
        }}
      >
        查看逻辑
      </Button>
    ),
  },
], []);

  // 优化回调函数
  const handleAssigneeChange = useCallback((key, value) => {
    setData(prev => prev.map(item =>
      item.key === key ? { ...item, assignee: value } : item
    ));
  }, []);

  const handleDelete = useCallback((key) => {
    setData(prev => prev.filter(item => item.key !== key));
  }, []);

  // 分析处理
  const handleAnalyze = async (values) => {
    setLoading(true);
    setLoadingType('analyze');
    try {
      const response = await api.post('/analyze', {
        jira_url: values.jiraUrl,
        cookies: values.cookieInput,
      });
      console.log('API响应数据:', response.data); // 新增调试日志

      setData(response.data.results.map((item, index) => ({
        key: index,
        ...item,
        assignee: item.assignee || '',
        reasoning: item.reasoning || '无分析记录' // 确保字段存在
      })));

      notification.success({ message: '数据分析成功' });
    } catch (error) {
      console.error('分析错误:', error);
    } finally {
      setLoading(false);
      setLoadingType('');
    }
  };

  // 分配处理
  const handleConfirm = async () => {
    setLoading(true);
    setLoadingType('assign');
    try {
      await api.post('/assign', {
        data,  // 原有数据
        cookies: form.getFieldValue('cookieInput')
      });
      notification.success({ message: '分配任务成功' });
    } catch (error) {
      console.error('分配错误:', error);
    } finally {
      setLoading(false);
      setLoadingType('');
    }
  };

  // 新增标签处理方法
  const handleAddLabel = async (issueId) => {
    try {
      await api.post('/add-label', {
        issueId,
        labels: "重点问题分析",
        cookieInput: form.getFieldValue('cookieInput')
      });

      notification.success({
        message: '标签添加成功',
        description: `已为问题 ${issueId} 添加标签`
      });
    } catch (error) {
      notification.error({
        message: '标签添加失败',
        description: error.response?.data?.error || '请检查网络连接'
      });
    }
  };

  // 在Table组件中添加footer
  const tableFooter = () => (
    <div style={{ textAlign: 'right', padding: '8px 16px' }}>
      <Tag color="blue">总行数: {data.length}</Tag>
    </div>
  );

  // 新增分析详情弹窗组件
  // 修改AnalysisDetail组件
// 修改后的AnalysisDetail组件
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



  // Cookie验证
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
    <Card
      title="JIRA 数据分析与分配系统"
      headStyle={{ background: '#f0f2f5' }}
      style={containerStyle}
    >
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
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              style={{ width: 120 }}
            >
              开始分析
            </Button>
            <Button
              type="primary"
              onClick={handleConfirm}
              disabled={!data.length || loading}
              style={{ width: 120 }}
            >
              确认分配
            </Button>
          </Space>
        </Form.Item>
      </Form>

      <Spin
        tip={`正在${loadingType === 'analyze' ? '分析数据' : '分配任务'}...`}
        spinning={loading}
        indicator={<LoadingOutlined spin />}
      >
        <Table
          columns={columns}
          dataSource={data}
          bordered
          pagination={false}
          scroll={{ y: 500 }}
          rowClassName={(_, index) => index % 2 === 0 ? 'even-row' : 'odd-row'}
          footer={tableFooter}  // 添加footer
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

export default App;
