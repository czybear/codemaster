import { memo, useEffect, useState } from 'react';
import { parseUrlParams } from 'Utils/urlUtils.js';
import routes from './Router/index';
import { useRoutes } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { useSystemStore } from 'stores/useSystemStore.js';
import i18n from './i18n.js';
import { inWechat, wechatLogin } from 'constants/uiConstants.js';
import { getBoolEnv } from 'Utils/envUtils.js';
import { userInfoStore } from 'Service/storeUtil.js';
import { getCourseInfo } from './Api/course.js';
import { useEnvStore } from 'stores/envStore.js';
import { useUserStore } from 'stores/useUserStore.js';
import { useShallow } from 'zustand/react/shallow';
import { selectDefaultLanguage } from 'constants/userConstants.js';
import { useCourseStore } from 'stores/useCourseStore.js';

const initializeEnvData = async () => {
  const {
    updateAppId,
    updateCourseId,
    updateAlwaysShowLessonTree,
    updateUmamiWebsiteId,
    updateUmamiScriptSrc,
    updateEruda,
    updateBaseURL,
    updateLogoHorizontal,
    updateLogoVertical,
    updateEnableWxcode,
    updateSiteUrl,
  } = useEnvStore.getState();
  const fetchEnvData = async () => {
    try {
      const res = await fetch('/config/env', {
        method: 'POST',
        referrer: 'no-referrer',
      });
      if (res.ok) {
        const data = await res.json();
        await updateCourseId(data?.REACT_APP_COURSE_ID || '');
        await updateAppId(data?.REACT_APP_APP_ID || '');
        await updateAlwaysShowLessonTree(
          data?.REACT_APP_ALWAYS_SHOW_LESSON_TREE || 'false'
        );
        await updateUmamiWebsiteId(data?.REACT_APP_UMAMI_WEBSITE_ID || '');
        await updateUmamiScriptSrc(data?.REACT_APP_UMAMI_SCRIPT_SRC || '');
        await updateEruda(data?.REACT_APP_ERUDA || 'false');
        await updateBaseURL(data?.REACT_APP_BASEURL || '');
        await updateLogoHorizontal(data?.REACT_APP_LOGO_HORIZONTAL || '');
        await updateLogoVertical(data?.REACT_APP_LOGO_VERTICAL || '');
        await updateEnableWxcode(data?.REACT_APP_ENABLE_WXCODE);
        await updateSiteUrl(data?.REACT_APP_SITE_URL);
      }
    } catch (error) {
    } finally {
      let { umamiWebsiteId, umamiScriptSrc } = useEnvStore.getState();
      if (getBoolEnv('eruda')) {
        import('eruda').then((eruda) => eruda.default.init());
      }
      const loadUmamiScript = () => {
        if (umamiScriptSrc && umamiWebsiteId) {
          const script = document.createElement('script');
          script.defer = true;
          script.src = umamiScriptSrc;
          script.setAttribute('data-website-id', umamiWebsiteId);
          document.head.appendChild(script);
        }
      };
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadUmamiScript);
      } else {
        loadUmamiScript();
      }
    }
  };
  await fetchEnvData();
};
const RouterView = () => useRoutes(routes);

const App = () => {
  const [envDataInitialized, setEnvDataInitialized] = useState(false);

  useEffect(() => {
    const initialize = async () => {
      await initializeEnvData();
      setEnvDataInitialized(true);
    };
    initialize();
  }, []);

  const {
    updateChannel,
    channel,
    wechatCode,
    updateWechatCode,
    setShowVip,
    updateLanguage,
  } = useSystemStore();

  const browserLanguage = selectDefaultLanguage(
    navigator.language || navigator.languages[0]
  );

  const [language] = useState(browserLanguage);

  const courseId = useEnvStore((state) => state.courseId);
  const updateCourseId = useEnvStore((state) => state.updateCourseId);
  const enableWxcode = useEnvStore((state) => state.enableWxcode);

  const { updateCourseName } = useCourseStore(
    useShallow((state) => ({
      updateCourseName: state.updateCourseName,
    }))
  );

  useEffect(() => {
    if (!envDataInitialized) return;
    const userInfo = userInfoStore.get();
    if (userInfo) {
      updateLanguage(userInfo.language);
    } else {
      updateLanguage(browserLanguage);
    }
  }, [browserLanguage, updateLanguage, envDataInitialized]);

  const [loading, setLoading] = useState(true);
  const params = parseUrlParams();
  const currChannel = params.channel || '';

  if (channel !== currChannel) {
    updateChannel(currChannel);
  }

  useEffect(() => {
    console.log('envDataInitialized...', envDataInitialized);
    if (!envDataInitialized) return;
    if (enableWxcode && inWechat()) {
      const { appId } = useEnvStore.getState();
      setLoading(true);
      const currCode = params.code;
      if (!currCode) {
        console.log('wechat login');
        wechatLogin({
          appId,
        });
        return;
      }
      if (currCode !== wechatCode) {
        updateWechatCode(currCode);
      }
    }
    setLoading(false);
  }, [
    params.code,
    updateWechatCode,
    wechatCode,
    envDataInitialized,
    enableWxcode,
  ]);

  useEffect(() => {
    const fetchCourseInfo = async () => {
      if (!envDataInitialized) return;
      if (params.courseId) {
        await updateCourseId(params.courseId);
      }
    };
    fetchCourseInfo();
  }, [envDataInitialized, updateCourseId, courseId, params.courseId]);

  useEffect(() => {
    const fetchCourseInfo = async () => {
      if (!envDataInitialized) return;
      if (courseId) {
        try {
          const resp = await getCourseInfo(courseId);
          if (resp.data) {
            setShowVip(resp.data.course_price > 0);
            updateCourseName(resp.data.course_name);
          } else {
            window.location.href = '/404';
          }
        } catch (error) {
          window.location.href = '/404';
        }
      }
    };
    fetchCourseInfo();
  }, [courseId, envDataInitialized, setShowVip, updateCourseName]);

  useEffect(() => {
    if (!envDataInitialized) return;
    console.log('i18n.changeLanguage(language)', language);
    i18n.changeLanguage(language);
    updateLanguage(language);
  }, [language, envDataInitialized, updateLanguage]);

  useEffect(() => {
    if (!envDataInitialized) return;
    const checkLogin = async () => {
      setLoading(true);
      await useUserStore.getState().checkLogin();
      setLoading(false);
    };
    checkLogin();
  }, [envDataInitialized]);

  return (
    <ConfigProvider locale={language}>
      {!loading && <RouterView></RouterView>}
    </ConfigProvider>
  );
};

export default memo(App);
