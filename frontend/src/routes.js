/* eslint-disable */

// Material Dashboard 2 React layouts
import Dashboard from "layouts/dashboard";
import Tables from "layouts/tables";
import Trade from "layouts/trade";
import SignIn from "layouts/authentication/sign-in";
import SignUp from "layouts/authentication/sign-up";
import LinkCoinbase from "layouts/link-coinbase";

// @mui icons
import Icon from "@mui/material/Icon";

const routes = [
  {
    type: "collapse",
    name: "Dashboard",
    key: "dashboard",
    icon: <Icon fontSize="small">dashboard</Icon>,
    route: "/dashboard",
    component: <Dashboard />,
  },
  /*
  {
    type: "collapse",
    name: "Trade History",
    key: "trade-history",
    icon: <Icon fontSize="small">table_view</Icon>,
    route: "/trade-history",
    component: <TablesHistory />,
  },*/
  {
    type: "collapse",
    name: "Trade",
    key: "trade",
    icon: <Icon fontSize="small">receipt_long</Icon>,
    route: "/trade",
    component: <Trade />,
  },
  {
    key: "sign-in",
    route: "/authentication/sign-in",
    component: <SignIn />,
  },
  {
    key: "sign-up",
    route: "/authentication/sign-up",
    component: <SignUp />,
  },
  {
    key: "link-coinbase",
    route: "/link-coinbase",
    component: <LinkCoinbase />,
  }
];

export default routes;

