import React, { useState, useEffect, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import mermaid from 'mermaid';
import { 
  BookOpen, 
  Folder, 
  Tag, 
  ChevronRight, 
  ChevronDown, 
  Moon, 
  Sun, 
  RefreshCw, 
  Search, 
  Menu, 
  Book, 
  FileText, 
  Layers, 
  HelpCircle,
  Code2,
  ExternalLink,
  ChevronLeft,
  Calendar,
  Layers2
} from 'lucide-react';
import './App.css';

// Initialize Mermaid
mermaid.initialize({
  startOnLoad: true,
  theme: 'dark',
  securityLevel: 'loose',
});

// Helper component to render Mermaid diagrams in React
const MermaidElement = ({ chart }) => {
  const [svg, setSvg] = useState('');
  const elementId = useRef(`mermaid-${Math.random().toString(36).substr(2, 9)}`);

  useEffect(() => {
    const renderChart = async () => {
      try {
        const { svg: renderedSvg } = await mermaid.render(elementId.current, chart);
        setSvg(renderedSvg);
      } catch (err) {
        console.error("Mermaid render error:", err);
        setSvg(`<pre class="mermaid-error" style="color: var(--error);">${chart}</pre>`);
      }
    };
    renderChart();
  }, [chart]);

  return <div className="mermaid-chart" dangerouslySetInnerHTML={{ __html: svg }} />;
};

// Pre-process markdown to replace GitHub-style alerts with standard Bold prefix
// This allows custom blockquote renderer to detect the alert type.
const processAlerts = (markdown) => {
  if (!markdown) return '';
  return markdown
    .replace(/>\s*\[!NOTE\]\s*/gi, '> **Note:** ')
    .replace(/>\s*\[!TIP\]\s*/gi, '> **Tip:** ')
    .replace(/>\s*\[!WARNING\]\s*/gi, '> **Warning:** ')
    .replace(/>\s*\[!IMPORTANT\]\s*/gi, '> **Important:** ')
    .replace(/>\s*\[!CAUTION\]\s*/gi, '> **Caution:** ');
};

function App() {
  const [projectList, setProjectList] = useState([]);
  const [currentProject, setCurrentProject] = useState('');
  const [vaultMeta, setVaultMeta] = useState(null);
  const [selectedPath, setSelectedPath] = useState('');
  const [markdownContent, setMarkdownContent] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [projectsMeta, setProjectsMeta] = useState({});
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Apply theme class
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Load project list
  useEffect(() => {
    setLoading(true);
    fetch('./vault/projects.json')
      .then(res => {
        if (!res.ok) throw new Error('프로젝트 목록을 불러오지 못했습니다.');
        return res.json();
      })
      .then(data => {
        setProjectList(data);
        setCurrentProject(''); // Start in Dashboard mode
      })
      .catch(() => {
        setProjectList(['git-wiki-generator']);
        setCurrentProject(''); // Fallback to Dashboard
      })
      .finally(() => setLoading(false));
  }, []);

  // Fetch metadata for all projects (for dashboard cards)
  useEffect(() => {
    if (projectList.length === 0) return;
    
    const fetches = projectList.map(proj => 
      fetch(`./vault/${proj}/vault_meta.json`)
        .then(res => {
          if (!res.ok) throw new Error();
          return res.json();
        })
        .then(meta => ({ proj, meta, error: false }))
        .catch(() => ({ proj, meta: null, error: true }))
    );

    Promise.all(fetches)
      .then(results => {
        const metaMap = {};
        results.forEach(r => {
          if (!r.error && r.meta) {
            metaMap[r.proj] = r.meta;
          }
        });
        setProjectsMeta(metaMap);
      })
      .catch(() => {});
  }, [projectList]);

  // Load project vault metadata
  useEffect(() => {
    if (!currentProject) {
      setVaultMeta(null);
      return;
    }
    setLoading(true);
    setError(null);
    fetch(`./vault/${currentProject}/vault_meta.json`)
      .then(res => {
        if (!res.ok) throw new Error(`'${currentProject}' 프로젝트의 메타데이터를 불러오지 못했습니다.`);
        return res.json();
      })
      .then(meta => {
        setVaultMeta(meta);
        setSelectedPath('overview.md');
      })
      .catch(err => {
        setError(err.message);
        setVaultMeta(null);
      })
      .finally(() => setLoading(false));
  }, [currentProject]);

  // Load selected markdown content
  useEffect(() => {
    if (!currentProject || !selectedPath) return;
    setLoading(true);
    
    const cleanPath = selectedPath.endsWith('.md') ? selectedPath : `${selectedPath}.md`;
    
    fetch(`./vault/${currentProject}/${cleanPath}`)

      .then(res => {
        if (!res.ok) throw new Error(`문서를 불러오지 못했습니다: ${cleanPath}`);
        return res.text();
      })
      .then(text => {
        setMarkdownContent(processAlerts(text));
        setError(null);
      })
      .catch(err => {
        setMarkdownContent('');
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [currentProject, selectedPath]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const handleRefresh = () => {
    if (!currentProject) return;
    setLoading(true);
    // Reload metadata and current page
    fetch(`./vault/${currentProject}/vault_meta.json?t=${Date.now()}`)
      .then(res => res.json())
      .then(meta => setVaultMeta(meta))
      .catch(() => {});

    const cleanPath = selectedPath.endsWith('.md') ? selectedPath : `${selectedPath}.md`;
    fetch(`./vault/${currentProject}/${cleanPath}?t=${Date.now()}`)
      .then(res => res.text())
      .then(text => setMarkdownContent(processAlerts(text)))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  const navigateTo = useCallback((path) => {
    // Standardise targets
    let target = path;
    if (target.endsWith('.md')) {
      target = target.substring(0, target.length - 3);
    }
    setSelectedPath(target);
  }, []);

  // Custom components for ReactMarkdown renderer
  const customMarkdownComponents = {
    // Render code blocks (with custom support for Mermaid)
    code: ({ className, children, ...props }) => {
      const match = /language-(\w+)/.exec(className || '');
      const codeString = String(children).replace(/\n$/, '');
      const isInline = !className;
      
      if (match && match[1] === 'mermaid') {
        return <MermaidElement chart={codeString} />;
      }
      
      return isInline ? (
        <code className={className} {...props}>
          {children}
        </code>
      ) : (
        <pre className={className}>
          <code {...props}>{children}</code>
        </pre>
      );
    },
    // Intercept internal relative markdown links
    a: ({ href, children, ...props }) => {
      if (href && !href.startsWith('http') && !href.startsWith('file://')) {
        return (
          <a 
            href="#" 
            onClick={(e) => {
              e.preventDefault();
              let targetPath = decodeURIComponent(href);
              if (targetPath.startsWith('./')) targetPath = targetPath.substring(2);
              if (targetPath.startsWith('/')) targetPath = targetPath.substring(1);
              navigateTo(targetPath);
            }}
            {...props}
          >
            {children}
          </a>
        );
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" className="external-link" {...props}>
          {children}
          {href && href.startsWith('file://') && <Code2 size={13} style={{ marginLeft: '4px', display: 'inline' }} />}
          {href && !href.startsWith('file://') && <ExternalLink size={12} style={{ marginLeft: '4px', display: 'inline' }} />}
        </a>
      );
    },
    // Customize blockquotes to render dynamic alerts
    blockquote: ({ children }) => {
      let alertClass = '';
      const firstChild = children[0];
      if (firstChild && firstChild.props && firstChild.props.children) {
        const firstText = Array.isArray(firstChild.props.children) 
          ? firstChild.props.children[0] 
          : firstChild.props.children;
        if (typeof firstText === 'string') {
          if (firstText.startsWith('Note:')) alertClass = 'alert-note';
          else if (firstText.startsWith('Tip:')) alertClass = 'alert-tip';
          else if (firstText.startsWith('Warning:')) alertClass = 'alert-warning';
          else if (firstText.startsWith('Important:')) alertClass = 'alert-important';
          else if (firstText.startsWith('Caution:')) alertClass = 'alert-caution';
        }
      }
      return <blockquote className={alertClass}>{children}</blockquote>;
    }
  };

  // Filter components/versions based on search query
  const matchesSearch = (name) => {
    if (!searchQuery) return true;
    return name.toLowerCase().includes(searchQuery.toLowerCase());
  };

  if (projectList.length === 0 && loading) {
    return (
      <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <div className="loadingSpinner">
          <div className="spinner"></div>
          <span>프로젝트 목록 불러오는 중...</span>
        </div>
      </div>
    );
  }

  if (!currentProject) {
    return (
      <div className="container" style={{ overflowY: 'auto' }}>
        <div className="dashboardContainer">
          <header className="dashboardHeader">
            <h1 className="dashboardTitle">Git Wiki Dashboard</h1>
            <p className="dashboardSubtitle">
              로컬 Git 저장소를 분석하여 구축된 개발 위키 리스트입니다.
              <br />
              원하시는 프로젝트의 위키 볼트(Vault)를 선택하여 상세 분석 문서를 확인하세요.
            </p>
          </header>

          <div className="dashboardGrid">
            {projectList.map(proj => {
              const meta = projectsMeta[proj];
              const projectType = meta?.projectType || 'general';
              const version = meta?.version || 'unknown';
              const versionsCount = meta?.versions?.length || 0;
              const componentsCount = meta?.components?.length || 0;
              const decisionsCount = meta?.decisions?.length || 0;

              return (
                <div 
                  key={proj} 
                  className="projectCard"
                  onClick={() => setCurrentProject(proj)}
                >
                  <div className="cardHeader">
                    <div className="cardIconBox">
                      <Folder size={28} />
                    </div>
                    <span className="cardTypeBadge">
                      {projectType}
                    </span>
                  </div>

                  <div className="cardMeta">
                    <h3 className="cardTitle">{proj}</h3>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      버전: {version}
                    </span>
                  </div>

                  <div className="cardStats">
                    <div className="cardStatItem">
                      <span className="cardStatValue">{versionsCount}</span>
                      <span className="cardStatLabel">릴리즈</span>
                    </div>
                    <div className="cardStatItem">
                      <span className="cardStatValue">{componentsCount}</span>
                      <span className="cardStatLabel">컴포넌트</span>
                    </div>
                    <div className="cardStatItem">
                      <span className="cardStatValue">{decisionsCount}</span>
                      <span className="cardStatLabel">의사결정</span>
                    </div>
                  </div>

                  <div className="cardFooter">
                    <span>위키 진입하기</span>
                    <ChevronRight size={16} />
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ 
            marginTop: '3.5rem', 
            display: 'flex', 
            gap: '1rem',
            alignItems: 'center'
          }}>
            <button 
              className="actionButton"
              onClick={toggleTheme}
              title={theme === 'dark' ? '라이트 모드 전환' : '다크 모드 전환'}
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              테마 설정
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      {/* Sidebar Panel */}
      <aside className={`sidebar ${!isSidebarOpen ? 'sidebarCollapsed' : ''}`}>
        <div className="sidebarHeader">
          <div className="logoArea">
            <BookOpen className="logoIcon" size={24} />
            <span className="logoTitle">Git Wiki Viewer</span>
          </div>

          {/* Search Bar */}
          <div className="searchWrapper">
            <Search className="searchIcon" size={16} />
            <input 
              type="text" 
              placeholder="파일 및 메뉴 검색..." 
              className="searchInput"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        <div className="sidebarContent">
          {/* Back to dashboard button */}
          <div className="backToProjects" onClick={() => setCurrentProject('')}>
            <ChevronLeft size={16} />
            <span>프로젝트 목록으로</span>
          </div>

          {vaultMeta && (
            <>
              {/* Quick Pages */}
              <div className="navSection">
                <span className="sectionHeader">기본 안내</span>
                <div 
                  className={`navItem ${selectedPath === 'overview' ? 'navItemActive' : ''}`}
                  onClick={() => navigateTo('overview')}
                >
                  <Book size={16} />
                  <span className="itemLabel">프로젝트 개요</span>
                </div>
                <div 
                  className={`navItem ${selectedPath === 'log' ? 'navItemActive' : ''}`}
                  onClick={() => navigateTo('log')}
                >
                  <Calendar size={16} />
                  <span className="itemLabel">릴리즈 타임라인</span>
                </div>
                <div 
                  className={`navItem ${selectedPath === 'index' ? 'navItemActive' : ''}`}
                  onClick={() => navigateTo('index')}
                >
                  <FileText size={16} />
                  <span className="itemLabel">전체 위키 인덱스</span>
                </div>
              </div>

              {/* Versions List */}
              {vaultMeta.versions && vaultMeta.versions.length > 0 && (
                <div className="navSection">
                  <span className="sectionHeader">🏷️ 릴리즈 버전 목록</span>
                  {vaultMeta.versions.filter(matchesSearch).map(version => (
                    <div 
                      key={version}
                      className={`navItem ${selectedPath === `versions/${version}` ? 'navItemActive' : ''}`}
                      onClick={() => navigateTo(`versions/${version}`)}
                    >
                      <Tag size={14} />
                      <span className="itemLabel">{version}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Components List */}
              {vaultMeta.components && vaultMeta.components.length > 0 && (
                <div className="navSection">
                  <span className="sectionHeader">📂 컴포넌트 & 모듈</span>
                  {vaultMeta.components.filter(matchesSearch).map(comp => (
                    <div 
                      key={comp}
                      className={`navItem ${selectedPath === `components/${comp}` ? 'navItemActive' : ''}`}
                      onClick={() => navigateTo(`components/${comp}`)}
                    >
                      <Layers size={14} />
                      <span className="itemLabel">{comp}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Decisions List */}
              {vaultMeta.decisions && vaultMeta.decisions.length > 0 && (
                <div className="navSection">
                  <span className="sectionHeader">💡 자연어 탐색 및 의사결정</span>
                  {vaultMeta.decisions.filter(matchesSearch).map(dec => (
                    <div 
                      key={dec}
                      className={`navItem ${selectedPath === `decisions/${dec}` ? 'navItemActive' : ''}`}
                      onClick={() => navigateTo(`decisions/${dec}`)}
                    >
                      <HelpCircle size={14} />
                      <span className="itemLabel">{dec.replace(/_/g, ' ')}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="contentArea">
        <header className="contentHeader">
          <div className="headerLeft">
            <button 
              className="toggleButton"
              onClick={() => setIsSidebarOpen(prev => !prev)}
              title="사이드바 토글"
            >
              <Menu size={18} />
            </button>
            <div className="breadcrumb">
              <span>프로젝트</span>
              <ChevronRight size={14} />
              <span className="breadcrumbCurrent">{currentProject}</span>
              {selectedPath && (
                <>
                  <ChevronRight size={14} />
                  <span className="breadcrumbCurrent">{selectedPath.replace(/^(versions|components|decisions)\//, '')}</span>
                </>
              )}
            </div>
          </div>

          <div className="headerRight">
            {vaultMeta && (
              <span className="metaInfo">
                {vaultMeta.projectType !== 'unknown' ? vaultMeta.projectType : '일반'} 프로젝트
              </span>
            )}
            <button 
              className="actionButton"
              onClick={handleRefresh}
              title="새로고침"
            >
              <RefreshCw size={16} className={loading ? 'spinner' : ''} />
            </button>
            <button 
              className="actionButton"
              onClick={toggleTheme}
              title={theme === 'dark' ? '라이트 모드 전환' : '다크 모드 전환'}
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          </div>
        </header>

        <div className="contentBody">
          <div className="contentWrapper">
            {loading && !markdownContent && (
              <div className="loadingSpinner">
                <div className="spinner"></div>
                <span>문서 불러오는 중...</span>
              </div>
            )}

            {error && (
              <div className="errorBox">
                <HelpCircle className="errorIcon" size={48} />
                <h3 className="errorTitle">오류 발생</h3>
                <p className="errorText">{error}</p>
                <button className="welcomeButton" onClick={handleRefresh}>다시 시도</button>
              </div>
            )}

            {!loading && !error && markdownContent && (
              <article className="markdown-body">
                <ReactMarkdown 
                  components={customMarkdownComponents}
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw]}
                >
                  {markdownContent}
                </ReactMarkdown>
              </article>
            )}

            {!loading && !error && !markdownContent && !vaultMeta && (
              <div className="welcomeCard">
                <BookOpen className="welcomeIcon" size={64} />
                <h2 className="welcomeTitle">문서를 불러오는 중이거나 데이터가 없습니다</h2>
                <p className="welcomeText">
                  해당 프로젝트의 개요 문서(overview.md)가 존재하지 않거나 데이터가 비어 있습니다.
                </p>
                <button className="welcomeButton" onClick={() => setCurrentProject('')}>
                  대시보드로 돌아가기
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
