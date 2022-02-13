import React, { useState, useEffect } from "react";
import { Nav, NavItem } from "react-bootstrap";
import { NavDropdown } from "react-bootstrap";
import { Navbar } from "react-bootstrap";
import axios from "axios";

const CharMenu = ({ character_id }) => {
  const [menus, setState] = useState({
    cats: [],
  });

  useEffect(() => {
    axios.get(`/audit/api/account/menu`).then((res) => {
      const cats = res.data;
      setState({ cats });
    });
  }, []);

  return (
    <Navbar fluid collapseOnSelect>
      <Nav>
        <NavItem key="Overview" href={`#/account/status`}>
          Overview
        </NavItem>
        <NavItem key="Public Data" href={`#/account/pubdata`}>
          Public Data
        </NavItem>
        {menus.cats.map((cat) => {
          return (
            <NavDropdown id={cat.name} title={cat.name} key={cat.name}>
              {cat.links.map((link) => {
                return (
                  <NavItem key={link.name} href={`#${link.link}`}>
                    {link.name}
                  </NavItem>
                );
              })}
            </NavDropdown>
          );
        })}
      </Nav>
    </Navbar>
  );
};

export default CharMenu;