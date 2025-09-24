import {
  OverlayScrollbarsComponent,
  type OverlayScrollbarsComponentProps,
} from "overlayscrollbars-react";

interface ScrollContainerProps extends OverlayScrollbarsComponentProps {
  children: React.ReactNode;
}

function ScrollContainer({ children, ...props }: ScrollContainerProps) {
  return (
    <OverlayScrollbarsComponent
      defer
      options={{ scrollbars: { autoHide: "leave", autoHideDelay: 100 } }}
      {...props}
    >
      {children}
    </OverlayScrollbarsComponent>
  );
}

export default ScrollContainer;
