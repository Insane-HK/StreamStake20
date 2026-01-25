// Layout.jsx
import { Outlet } from "react-router-dom";
import Navbar from "./Components/Navbar";
import { WalletProvider } from "./context/WalletContext";

function Layout() {
    return (
        <WalletProvider>
            <Navbar />
            <Outlet />
        </WalletProvider>
    );
}

export default Layout;