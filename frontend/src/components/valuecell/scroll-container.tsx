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
      options={{ scrollbars: { autoHide: "leave" } }}
      {...props}
    >
      {children}
    </OverlayScrollbarsComponent>
  );
}

export default ScrollContainer;
