import React from 'react';
import { useNavigate } from 'react-router-dom';

const Footer = () => {
    const navigate = useNavigate();

    return (
        <div style={styles.footer}>
            <button style={styles.button} onClick={() => navigate('/')}>Home</button>
        </div>
    );
}

const styles = {
    footer: {
        position: 'fixed',
        bottom: '0',
        width: '100%',
        display: 'flex',
        justifyContent: 'space-around',
        backgroundColor: '#f8f8f8',
        padding: '10px 0',
    },
    button: {
        padding: '10px',
        fontSize: '14px',
        cursor: 'pointer',
        border: 'none',
        backgroundColor: '#007bff',
        color: 'white',
        borderRadius: '4px',
    },
};

export default Footer;