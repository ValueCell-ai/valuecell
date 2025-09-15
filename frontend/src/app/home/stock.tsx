import { useParams } from "react-router";

function Stock() {
  const { stockId } = useParams();

  return <div>Stock {stockId}</div>;
}

export default Stock;
