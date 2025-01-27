import {
  INTERACTION_OUTPUT_TYPE,
  INTERACTION_TYPE,
} from 'constants/courseConstants.js';
import styles from './ChatInputButton.module.scss';
import MainButton from 'Components/MainButton.jsx';
import { useEffect } from 'react';
import { memo } from 'react';
import { registerInteractionType } from '../interactionRegistry';
import { useShallow } from 'zustand/react/shallow';
import { useUiLayoutStore } from 'stores/useUiLayoutStore.js';
import { useHotkeys } from 'react-hotkeys-hook';
import { SHORTCUT_IDS, genHotKeyIdentifier } from 'Service/shortcut.js';

export const ChatInputButton = ({ type, props, onClick, disabled }) => {
  const onBtnClick = () => {
    if (type === INTERACTION_TYPE.NEXT_CHAPTER) {
      onClick?.(INTERACTION_OUTPUT_TYPE.NEXT_CHAPTER, {
        lessonId: props.lessonId,
      });
      return;
    }

    if (type === INTERACTION_TYPE.ORDER) {
      onClick?.(INTERACTION_OUTPUT_TYPE.ORDER, { orderId: props.value });
      return
    }
    if (type === INTERACTION_TYPE.NONBLOCK_ORDER) {
      onClick?.(INTERACTION_OUTPUT_TYPE.NONBLOCK_ORDER, { orderId: props.value });
      return
    }
    if (type === INTERACTION_TYPE.REQUIRE_LOGIN) {
      onClick?.(INTERACTION_OUTPUT_TYPE.REQUIRE_LOGIN, props.value);
      return;
    }

    onClick?.(INTERACTION_OUTPUT_TYPE.CONTINUE, props.value);
  }

  const { inMacOs } = useUiLayoutStore(
    useShallow((state) => ({ inMacOs: state.inMacOs }))
  );

  useHotkeys(
    `${genHotKeyIdentifier(SHORTCUT_IDS.CONTINUE, inMacOs)}, enter`,
    () => {
      onBtnClick();
    },
    [onBtnClick]
  );

  return (
    <div className={styles.continueWrapper}>
      <MainButton
        className={styles.continueBtn}
        width="90%"
        disabled={disabled}
        onClick={onBtnClick}
      >
        {props.label}
      </MainButton>
    </div>
  );
};

const ChatInputButtonMemo = memo(ChatInputButton);
registerInteractionType(INTERACTION_TYPE.CONTINUE, ChatInputButtonMemo);
registerInteractionType(INTERACTION_TYPE.NEXT_CHAPTER, ChatInputButtonMemo);
registerInteractionType(INTERACTION_TYPE.ORDER, ChatInputButtonMemo);
registerInteractionType(INTERACTION_TYPE.NONBLOCK_ORDER, ChatInputButtonMemo);
registerInteractionType(INTERACTION_TYPE.REQUIRE_LOGIN, ChatInputButtonMemo);
export default ChatInputButtonMemo;
