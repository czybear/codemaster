import React, { memo, useRef, useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, ConfigProvider } from 'antd';
import classNames from 'classnames';
import styles from './ChatInteractionArea.module.scss';
import askIcon from '@Assets/newchat/light/svg-ask-16.svg';
import {
  INTERACTION_TYPE,
  INTERACTION_DISPLAY_TYPE,
} from 'constants/courseConstants.js';
import { getInteractionComponent } from './interactionRegistry';
import ChatInputText from './InputComponents/ChatInputText';
import AskButton from './InputComponents/AskButton';

// import all interaction components
const importAll = (r) => r.keys().forEach(r);
importAll(require.context('./InputComponents', true, /\.jsx$/));

export const ChatInteractionArea = ({
  type = INTERACTION_DISPLAY_TYPE.TEXT,
  props = {},
  onSend = (type, val, scriptId) => {},
  disabled = false,
  askButtonState = { askMode: false, total: 1, used: 0 },
  onSizeChange = ({ width, height }) => {},
}) => {
  const elemRef = useRef();
  const { t } = useTranslation();
  const [isInputVisible, setInputVisible] = useState(false);

  const onSendFunc = (type, val) => {
    if (disabled) {
      return;
    }
    onSend?.(type, val, props.scriptId);
  };

  const genRenderControl = () => {
    const Component = getInteractionComponent(type);
    if (Component) {
      return (
        <Component
          disabled={disabled}
          type={type}
          props={props}
          onClick={onSendFunc}
        />
      );
    }
    return <></>;
  };

  const resizeChange = useCallback(
    (e) => {
      onSizeChange?.({
        width: e.contentRect.width,
        height: e.contentRect.height,
      });
    },
    [onSizeChange]
  );

  const handleAskClick = () => {
    setInputVisible(!isInputVisible);
  };

  const onSendAsk = (type, val) => {
    setInputVisible(false);
    onSendFunc?.(INTERACTION_TYPE.ASK, val);
  };

  useEffect(() => {
    const resize = new ResizeObserver((e) => {
      if (!Array.isArray(e) || !e.length) return;
      for (const ent of e) {
        resizeChange(ent);
      }
    });
    resize.observe(elemRef?.current);
    // Destroy the observer in a timely manner (important!!!)
    const curr = elemRef?.current;
    return () => {
      resize.unobserve(curr);
    };
  }, [resizeChange]);

  return (
    <div
      className={classNames(styles.chatInputArea, disabled && styles.disabled)}
      ref={elemRef}
    >
      <div className={styles.controlContainer}>
        <div className={styles.controlWrapper}>
          <div className={styles.controlWrapperInner}>
            {!isInputVisible && genRenderControl()}{' '}
            {/* Display input box based on state */}
            {isInputVisible && (
              <ChatInputText
                id="askInput"
                onClick={onSendAsk}
                type="text"
                props={{ content: t('chat.askContent') }}
                visible={isInputVisible}
              />
            )}
          </div>
          {askButtonState.visible && (
            <AskButton
              className={styles.askButton}
              disabled={!askButtonState.askMode}
              total={askButtonState.total}
              used={askButtonState.used}
              onClick={handleAskClick}
            />
          )}
        </div>
      </div>
      <div className={styles.tipText}>{t('chat.chatTips')}</div>
    </div>
  );
};

export default memo(ChatInteractionArea);
